import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

TARGET_CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
PEST_NAMES = {
    1: "稻纵卷叶螟", 2: "稻眼蝶幼虫(稻青虫)", 3: "水稻潜叶蝇", 4: "二化螟", 5: "三化螟",
    6: "稻瘿蚊", 7: "稻秆蝇", 8: "褐飞虱", 9: "白背飞虱", 10: "灰飞虱"
}
class_mapping = {new_id: old_id for new_id, old_id in enumerate(TARGET_CLASSES)}

class PestVisionModel:
    def __init__(self, weight_path, device='cpu'):
        self.device = torch.device(device)
        self.model = self._load_model(weight_path)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def _load_model(self, path):
        model = models.resnet50(weights=None)
        model.fc = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.fc.in_features, len(TARGET_CLASSES)))
        # map_location='cpu' 确保服务器部署不报错
        model.load_state_dict(torch.load(path, map_location=self.device, weights_only=True))
        model.to(self.device)
        model.eval()
        return model

    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.nn.functional.softmax(outputs[0], dim=0)
            conf, idx = torch.max(probs, 0)
        return PEST_NAMES.get(class_mapping[idx.item()], "未知"), conf.item()
