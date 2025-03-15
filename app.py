from flask import Flask, render_template, request, send_from_directory, url_for, jsonify
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import openai
import requests
from io import BytesIO
import textwrap  # ✅ 确保导入 textwrap 以支持文本换行
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件
openai.api_key = os.getenv("OPENAI_API_KEY")

# 设置 OpenAI API Key

app = Flask(__name__)

# 确保 static 目录存在
os.makedirs('static', exist_ok=True)


def generate_welcome_message(guest_name, country, nights):
    """ 使用 OpenAI 生成个性化欢迎词 """
    client = openai.OpenAI(api_key=openai.api_key)
    prompt = f"""
    Generate a warm, personalized welcome message for a hotel guest. Follow these formats:

    Example 1:
    Welcome, James Miller from Australia! We’re delighted to have you at Magnificent Hotel for 5 days—may your journey be filled with breathtaking sights and Kathmandu’s warm spirit. Namaste! 

    Example 2:
    Namaste, Sofia Rodríguez from Spain! Enjoy your 3-day stay at Magnificent Hotel, where Kathmandu’s charm and warm hospitality await. Have a great time!

    Example 3:
    Dear Hiroshi Tanaka from Japan, welcome to Magnificent Hotel! May your 7-day stay be full of adventure, local flavors, and Kathmandu’s magic. We’re honored to host you!

    Now generate a similar message for:
    - Guest Name: {guest_name}
    - Country: {country}
    - Length of Stay: {nights} nights

    Make it warm, inviting, and aligned with Kathmandu’s hospitality.
    Keep the number of words in the text within 20 to 30
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def generate_image():
    """ 生成带有加德满都特色的背景图片 """
    image_prompt = """A warm and inviting digital postcard featuring iconic Kathmandu landmarks such as 
    Boudhanath Stupa, Swayambhunath Monkey Temple, Himalayan mountains, and colorful Nepalese prayer flags. 
    The art style should be warm, artistic, and visually appealing."""

    response = openai.images.generate(
        model="dall-e-3",  # 指定 DALL·E 3
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1  # 生成 1 张图片
    )

    return response.data[0].url


@app.route('/')
def home():
    return render_template('index.html', img_path=None)


@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'logo' not in request.files:
        return "No file uploaded", 400

    logo_file = request.files['logo']
    if logo_file.filename == '':
        return "No selected file", 400

    # 保存 Logo 到 static 目录
    logo_path = os.path.join("static", "hotel_logo.png")
    logo_file.save(logo_path)

    return "Logo uploaded successfully!", 200


@app.route('/generate', methods=['POST'])
def generate_card():
    guest_name = request.form.get('guest_name', 'Guest')
    country = request.form.get('country', 'Unknown')
    nights = request.form.get('nights', '1')
    # 生成个性化欢迎词
    welcome_text = generate_welcome_message(guest_name, country, nights)

    # 生成 AI 背景图
    image_url = generate_image()
    response = requests.get(image_url)
    background = Image.open(BytesIO(response.content)).convert("RGBA")  # 确保支持透明度

    # 叠加欢迎文本
    img_w, img_h = background.size
    draw = ImageDraw.Draw(background)
    font_size = max(int(img_w * 0.04), 40)  # 适当降低字体大小
    font_path = "static/fonts/Condiment-Regular.ttf"  # macOS 默认路径
    if not os.path.exists(font_path):
        font_path = "static/arial.ttf"  # 备用路径，可手动放置 arial.ttf

    font = ImageFont.truetype(font_path, font_size)  # 确保字体加载成功

    text_x = img_w // 2  # 水平居中
    text_y = img_h - 200  # 让文字在图片底部

    box_padding = 20
    bbox = draw.textbbox((0, 0), f"Welcome, {guest_name}!", font=font)
    box_w = bbox[2] - bbox[0]  # 计算文本宽度
    box_h = bbox[3] - bbox[1]  # 计算文本高度
    box_x = text_x - box_w // 2 - box_padding
    box_y = text_y - box_padding
    box_x2 = text_x + box_w // 2 + box_padding
    box_y2 = text_y + box_h + box_padding

    # **加载 Logo、Magnificent 和 Hotel**
    # **加载 Logo、Magnificent 和 Hotel**
    logo_path = "static/hotel_logo.png"
    magnificent_path = "static/magnificent.png"
    hotel_path = "static/hotel.png"

    if os.path.exists(logo_path) and os.path.exists(magnificent_path) and os.path.exists(hotel_path):
        logo = Image.open(logo_path).convert("RGBA")
        magnificent = Image.open(magnificent_path).convert("RGBA")
        hotel = Image.open(hotel_path).convert("RGBA")

        # **计算 Logo + Name 最大宽度**
        max_name_width = img_w * 0.6  # 旅馆名称 + Logo 占图片宽度 60% 以内

        # **确保 Logo 不变形**
        max_logo_width = int(img_w * 0.15)
        max_logo_height = int(img_h * 0.15)
        logo.thumbnail((max_logo_width, max_logo_height), Image.LANCZOS)

        # **让 Name 图片高度与 Logo 一致**
        new_height = logo.size[1]
        magnificent = magnificent.resize((int(magnificent.width * (new_height / magnificent.height)), new_height),
                                         Image.LANCZOS)
        hotel = hotel.resize((int(hotel.width * (new_height / hotel.height)), new_height), Image.LANCZOS)

        # **计算整体宽度**
        total_width = logo.size[0] + magnificent.size[0] + hotel.size[0] + 30  # 30 是间距

        # **如果超出最大宽度，整体缩放**
        if total_width > max_name_width:
            scale_factor = max_name_width / total_width
            logo = logo.resize((int(logo.size[0] * scale_factor), int(logo.size[1] * scale_factor)), Image.LANCZOS)
            magnificent = magnificent.resize(
                (int(magnificent.size[0] * scale_factor), int(magnificent.size[1] * scale_factor)), Image.LANCZOS)
            hotel = hotel.resize((int(hotel.size[0] * scale_factor), int(hotel.size[1] * scale_factor)), Image.LANCZOS)

        # **计算居中 X 坐标**
        start_x = (img_w - (logo.size[0] + magnificent.size[0] + hotel.size[0] + 30)) // 2
        logo_x, logo_y = start_x, 30
        magnificent_x, magnificent_y = logo_x + logo.size[0] + 10, logo_y
        hotel_x, hotel_y = magnificent_x + magnificent.size[0] + 10, logo_y

        # **粘贴 Logo + 旅馆名称**
        background.paste(logo, (logo_x, logo_y), logo)
        background.paste(magnificent, (magnificent_x, magnificent_y), magnificent)
        background.paste(hotel, (hotel_x, hotel_y), hotel)

        background.paste(magnificent, (magnificent_x, magnificent_y), magnificent)
        background.paste(hotel, (hotel_x, hotel_y), hotel)

    # **添加欢迎文字**
    # **自动换行**
    wrapped_text = "\n".join(textwrap.wrap(welcome_text, width=40))  # 40 个字符换行
    line_spacing = font_size + 15  # 控制行间距

    # **计算文本整体高度**
    text_lines = wrapped_text.split("\n")
    total_text_height = len(text_lines) * line_spacing

    # **调整文本起始位置**
    text_y = img_h - total_text_height - 50  # 让文本整体向上移动，避免超出图片底部

    # **逐行绘制**
    for i, line in enumerate(wrapped_text.split("\n")):
        draw.text((text_x, text_y + i * line_spacing), line, fill="white", font=font, anchor="mm", stroke_width=3,
                  stroke_fill="black")

    # 生成时间戳，防止缓存
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    img_filename = f"welcome_card_{timestamp}.png"
    img_path = os.path.join("static", img_filename)

    try:
        background.save(img_path)
        print(f"✅ Image saved successfully: {img_path}")
    except Exception as e:
        print(f"❌ Failed to save image: {e}")
        return render_template('index.html', img_path=None)

    # 生成图片 URL
    img_url = url_for('static', filename=img_filename, _external=True)

    return render_template('index.html', img_path=img_url)


# 确保 Flask 正确提供 static 目录
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
