import os


def scan_directory(directory='.', exclude_extensions=['.png', '.jpg','pyc','map'], exclude_dirs=['.git','staticfiles']):
    """
    扫描指定目录下的所有文件及其路径，排除特定扩展名的文件和指定的目录

    参数:
        directory (str): 要扫描的目录，默认为当前目录
        exclude_extensions (list): 要排除的文件扩展名，默认为['.png', '.jpg']
        exclude_dirs (list): 要排除的目录名，默认为['.git']

    返回:
        list: 文件路径列表
    """
    file_paths = []

    for root, dirs, files in os.walk(directory):
        # 原地修改dirs列表，排除指定目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            # 检查文件是否有被排除的扩展名
            if not any(file.lower().endswith(ext.lower()) for ext in exclude_extensions):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)

    return file_paths

def main():
    # 获取文件列表
    files = scan_directory()

    # 打印结果
    print(f"找到{len(files)}个文件(已排除.png、.jpg和.git文件):")
    for file_path in files:
        print(file_path)


if __name__ == "__main__":
    main()