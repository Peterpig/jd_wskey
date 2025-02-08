import os

from PIL import Image


def create_ico(image, ico_path):
    """创建Windows图标文件"""
    # 创建不同尺寸的图标
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_sizes = []

    for size in sizes:
        resized_img = image.resize(size, Image.Resampling.LANCZOS)
        icon_sizes.append(resized_img)

    # 确保icons目录存在
    os.makedirs(os.path.dirname(ico_path), exist_ok=True)

    # 保存.ico文件
    icon_sizes[0].save(
        ico_path, format="ICO", sizes=sizes, append_images=icon_sizes[1:]
    )


def create_icns(image, icns_path):
    """创建macOS图标文件"""
    # 创建临时工作目录
    iconset_path = icns_path.replace(".icns", ".iconset")
    os.makedirs(iconset_path, exist_ok=True)

    # 生成不同尺寸的图标
    sizes = [
        (16, 16),
        (32, 32),
        (128, 128),
        (256, 256),
        (512, 512),
        (32, 32),
        (64, 64),
        (256, 256),
        (512, 512),
        (1024, 1024),
    ]
    names = [
        "icon_16x16.png",
        "icon_32x32.png",
        "icon_128x128.png",
        "icon_256x256.png",
        "icon_512x512.png",
        "icon_16x16@2x.png",
        "icon_32x32@2x.png",
        "icon_128x128@2x.png",
        "icon_256x256@2x.png",
        "icon_512x512@2x.png",
    ]

    # 生成每个尺寸的图片
    for size, name in zip(sizes, names):
        resized_img = image.resize(size, Image.Resampling.LANCZOS)
        resized_img.save(os.path.join(iconset_path, name))

    # 使用iconutil转换为.icns (仅在macOS上可用)
    if os.system('iconutil -c icns -o "%s" "%s"' % (icns_path, iconset_path)) != 0:
        print("Warning: iconutil command failed. .icns file may not be created.")


def main():
    # 确保icons目录存在
    os.makedirs("icons", exist_ok=True)

    # 读取PNG图片
    with Image.open("utils/jd.png") as img:
        # 转换为RGBA模式
        img = img.convert("RGBA")

        # 创建Windows图标
        create_ico(img, "icons/icon.ico")

        # 在macOS上创建.icns文件
        if platform.system().lower() == "darwin":
            create_icns(img, "icons/icon.icns")

        print("Icon files created successfully!")


if __name__ == "__main__":
    import platform

    main()
