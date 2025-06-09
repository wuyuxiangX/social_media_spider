import os
import re
import subprocess
import glob  # 新增导入

def ensure_folders_exist(output_dir, base_path=""):
    if base_path:
        bili_video_path = f"{base_path}/bilibili_video"
        outputs_path = f"{base_path}/outputs"
    else:
        bili_video_path = "bili2text/bilibili_video"
        outputs_path = "outputs"
    
    if not os.path.exists(bili_video_path):
        os.makedirs(bili_video_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(outputs_path):
        os.makedirs(outputs_path)

def download_video(bv_number, base_path=""):
    """
    使用you-get下载B站视频。
    参数:
        bv_number: 字符串形式的BV号（不含"BV"前缀）或完整BV号
        base_path: 基础存储路径（可选）
    返回:
        文件路径
    """
    if not bv_number.startswith("BV"):
        bv_number = "BV" + bv_number
    video_url = f"https://www.bilibili.com/video/{bv_number}"
    
    if base_path:
        output_dir = f"{base_path}/bilibili_video/{bv_number}"
    else:
        output_dir = f"bilibili_video/{bv_number}"
    
    ensure_folders_exist(output_dir, base_path)
    print(f"使用you-get下载视频: {video_url}")
    try:
        result = subprocess.run(["you-get", "-l", "-o", output_dir, video_url], capture_output=True, text=True)
        if result.returncode != 0:
            print("下载失败:", result.stderr)
        else:
            print(result.stdout)
            print(f"视频已成功下载到目录: {output_dir}")
            video_files = glob.glob(os.path.join(output_dir, "*.mp4"))
            if video_files:
                # 删除xml文件
                xml_files = glob.glob(os.path.join(output_dir, "*.xml"))
                for xml_file in xml_files:
                    os.remove(xml_file)
            else:
                file_path = ""
    except Exception as e:
        print("发生错误:", str(e))
        file_path = ""
    return bv_number
