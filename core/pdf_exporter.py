import markdown
import pdfkit
import os

def export_md_to_pdf(md_content, output_path="governance_report.pdf"):
    """将 Markdown 渲染为带有精美样式的 PDF"""
    
    # 1. 将 Markdown 转换为 HTML
    html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])
    
    # 2. 注入 CSS 模板，强制使用文泉驿微米黑字体以支持中文
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: "WenQuanYi Zen Hei", "Microsoft YaHei", sans-serif;
                line-height: 1.6;
                color: #333333;
                padding: 2em;
            }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 1.5em; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 1em; }}
            th, td {{ border: 1px solid #dddddd; padding: 10px; text-align: left; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
            blockquote {{ border-left: 4px solid #4CAF50; margin: 0; padding-left: 1em; color: #555; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    # 3. 配置 pdfkit
    options = {
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'quiet': ''
    }
    
    # 4. 生成 PDF
    try:
        pdfkit.from_string(html_template, output_path, options=options)
        return output_path
    except Exception as e:
        print("\n" + "="*40)
        print("❌ PDF 导出底层错误详情:")
        print(str(e))
        print("="*40 + "\n")
        return None
