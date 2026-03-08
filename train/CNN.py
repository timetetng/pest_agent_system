import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.amp import GradScaler, autocast  # 修复了弃用警告
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
from tqdm import tqdm

# =================1. 配置参数=================
DATA_DIR = 'ip02-dataset'  
BATCH_SIZE = 16            
EPOCHS = 30                 
LEARNING_RATE = 0.001
NUM_WORKERS = 4

torch.backends.cudnn.benchmark = True 

TARGET_CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] 
NUM_CLASSES = len(TARGET_CLASSES)
MAX_SAMPLES_PER_CLASS = None
class_mapping = {old_id: new_id for new_id, old_id in enumerate(TARGET_CLASSES)}
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# =================2. 自定义 Dataset 类=================
class IP102Dataset(Dataset):
    def __init__(self, data_dir, phase, transform=None, target_classes=None, max_samples=None):
        self.phase = phase
        self.transform = transform
        self.image_labels = []
        
        txt_file = os.path.join(data_dir, f'{phase}.txt')
        img_dir = os.path.join(data_dir, 'classification', phase)
        
        class_counts = {cls: 0 for cls in target_classes} if target_classes else {}
        missing_count = 0
        
        with open(txt_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    img_name = os.path.basename(parts[0].strip("'\"")) 
                    label = int(parts[1])
                    
                    if label in target_classes:
                        if max_samples is None or class_counts[label] < max_samples:
                            img_path = os.path.join(img_dir, str(label), img_name)
                            if os.path.exists(img_path):
                                self.image_labels.append((img_path, label))
                                class_counts[label] += 1
                            else:
                                missing_count += 1
                                
        print(f"{phase} 集共成功加载 {len(self.image_labels)} 张图片，缺失 {missing_count} 张。")

    def __len__(self):
        return len(self.image_labels)

    def __getitem__(self, idx):
        img_path, original_label = self.image_labels[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        new_label = class_mapping[original_label]
        return image, new_label

# =================3. 数据增强=================
data_transforms = {
    'train': transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),   
        transforms.RandomRotation(30),     
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2), 
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        # 适度降低擦除概率，给模型一点喘息的空间
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.1)) 
    ]),
    'val': transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

# =================4. 训练循环=================
def train_model(model, dataloaders, dataset_sizes, criterion, optimizer, scheduler, num_epochs=EPOCHS):
    best_acc = 0.0
    scaler = GradScaler('cuda') # 修复了弃用警告

    for epoch in range(num_epochs):
        print(f'\nEpoch {epoch+1}/{num_epochs}')
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            if dataset_sizes[phase] == 0:
                continue

            pbar = tqdm(dataloaders[phase], desc=f"{phase.capitalize()}", leave=False)

            for inputs, labels in pbar:
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()

                with autocast('cuda', enabled=torch.cuda.is_available()):
                    with torch.set_grad_enabled(phase == 'train'):
                        outputs = model(inputs)
                        _, preds = torch.max(outputs, 1)
                        loss = criterion(outputs, labels)

                if phase == 'train':
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()

                batch_loss = loss.item() * inputs.size(0)
                batch_corrects = torch.sum(preds == labels.data).item()
                running_loss += batch_loss
                running_corrects += batch_corrects
                
                pbar.set_postfix({'loss': f"{loss.item():.4f}", 'acc': f"{batch_corrects/inputs.size(0):.4f}"})

            if phase == 'train':
                scheduler.step()

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects / dataset_sizes[phase]
            current_lr = optimizer.param_groups[0]['lr']
            print(f'{phase.capitalize()} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f} (LR: {current_lr:.6f})')

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                torch.save(model.state_dict(), 'best_resnet50_pests.pth')

    print(f'\n训练完成！最高验证集准确率: {best_acc:.4f}')
    return model

if __name__ == '__main__':
    image_datasets = {x: IP102Dataset(DATA_DIR, x, data_transforms[x], TARGET_CLASSES, MAX_SAMPLES_PER_CLASS)
                      for x in ['train', 'val']}
    
    dataloaders = {x: DataLoader(image_datasets[x], batch_size=BATCH_SIZE, shuffle=(x=='train'), 
                                 num_workers=NUM_WORKERS, pin_memory=True) 
                   for x in ['train', 'val']}
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}

    # 构建模型
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    
    # ---------------------------------------------------------
    # 【核心修改：渐进式解冻】
    # 1. 先把所有层冻结
    for param in model.parameters():
        param.requires_grad = False
        
    # 2. 仅解冻深层的 layer3 和 layer4，让它学习害虫的高级特征
    for name, param in model.named_parameters():
        if "layer3" in name or "layer4" in name:
            param.requires_grad = True
    # ---------------------------------------------------------
            
    num_ftrs = model.fc.in_features
    # 适度降低 Dropout 到 0.3
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(num_ftrs, NUM_CLASSES)
    )
    model = model.to(device)

    # 保留标签平滑，这对于 IP102 这种脏数据多的数据集很有效
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    
    # 将需要更新的参数分门别类
    backbone_params = [p for n, p in model.named_parameters() if ("layer3" in n or "layer4" in n) and p.requires_grad]
    fc_params = model.fc.parameters()

    # 降低 weight_decay 到 1e-3
    optimizer = optim.AdamW([
        {'params': backbone_params, 'lr': LEARNING_RATE * 0.1}, 
        {'params': fc_params, 'lr': LEARNING_RATE}          
    ], weight_decay=1e-3)

    scheduler = lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    trained_model = train_model(model, dataloaders, dataset_sizes, criterion, optimizer, scheduler, EPOCHS)
