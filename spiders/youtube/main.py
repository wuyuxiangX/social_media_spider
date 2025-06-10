"""
音频转字幕一条龙脚本
1. 切片音频
2. Whisper 识别
3. 输出字幕文件（txt）
依赖：pydub, speech2text.py
"""
import os
import time
import argparse
from pydub import AudioSegment
from ..bilibili.speech2text import run_analysis, load_whisper
import yt_dlp


def get_storage_base():
    """获取存储基础目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    storage_base = os.path.join(project_root, "storage", "youtube")
    
    # 确保所需目录存在
    directories = [
        os.path.join(storage_base, "downloads"),
        os.path.join(storage_base, "audio", "slice"),
        os.path.join(storage_base, "outputs")
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
    return storage_base


def search_youtube(query, max_results=5):
    """ 使用 yt-dlp 搜索 YouTube 视频并下载音频 """
    storage_base = get_storage_base()
    downloads_dir = os.path.join(storage_base, "downloads")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
        'outtmpl': os.path.join(downloads_dir, f'{query}_%(id)s.%(ext)s'),
        "default_search": f"ytsearch{max_results}",
    }

    downloaded_files = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(query, download=True)
            if 'entries' in info_dict:  # 搜索结果
                for entry in info_dict['entries']:
                    audio_file = os.path.join(downloads_dir, f"{query}_{entry['id']}.mp3")
                    downloaded_files.append({
                        "title": entry["title"],
                        "path": audio_file
                    })
            else:  # 单个视频
                audio_file = os.path.join(downloads_dir, f"{query}_{info_dict['id']}.mp3")
                downloaded_files.append({
                    "title": info_dict["title"],
                    "path": audio_file
                })

            return downloaded_files

        except Exception as e:
            print(f"搜索 YouTube 失败: {e}")
            return []


def split_audio(audio_path, output_folder, slice_length=45000):
    """
    将MP3音频切割为多个小片段。
    :param audio_path: 输入音频文件路径（.mp3）
    :param output_folder: 输出切片文件夹
    :param slice_length: 每个切片的长度（毫秒），默认45秒
    """
    audio = AudioSegment.from_mp3(audio_path)
    total_slices = (len(audio) + slice_length - 1) // slice_length
    os.makedirs(output_folder, exist_ok=True)
    for i in range(total_slices):
        start = i * slice_length
        end = start + slice_length
        slice_audio = audio[start:end]
        slice_path = os.path.join(output_folder, f"{i + 1}.mp3")
        slice_audio.export(slice_path, format="mp3")
        print(f"切片 {i + 1} 已保存: {slice_path}")


def audio_to_subtitle(audio_path, model="small", prompt="以下是普通话的句子。", slice_length=45000):
    storage_base = get_storage_base()
    
    # 1. 切片
    timestamp = time.strftime('%Y%m%d%H%M%S')
    slice_folder = os.path.join(storage_base, "audio", "slice", timestamp)
    split_audio(audio_path, slice_folder, slice_length)
    
    # 2. 加载whisper模型
    load_whisper(model)
    
    # 3. 识别并输出字幕
    output_path = os.path.join(storage_base, "outputs", f"{timestamp}.txt")
    run_analysis(timestamp, model=model, prompt=prompt, base_path=storage_base)
    print(f"字幕已输出到: {output_path}")
    return output_path


def main(query, max_results=5, model="small", prompt="以下是普通话的句子。", slice_length=45000):
    print("===== YouTube 音频搜索与字幕生成工具 =====")

    # 设置默认参数
    model = "small"  # 可选：tiny, base, small, medium, large
    prompt = "以下是普通话的句子。"  # 可自定义提示词
    slice_length = 45000  # 单位：毫秒

    # 获取存储路径
    storage_base = get_storage_base()
    print(f"文件将保存到: {storage_base}")

    print(f"正在搜索并下载: {query}")
    downloaded_files = search_youtube(query, max_results)
    if not downloaded_files:
        print("没有找到匹配的视频或下载失败")
        return

    # 使用下载的音频文件
    audio_list = [item["path"] for item in downloaded_files]
    print(f"已下载 {len(audio_list)} 个音频文件:")
    for i, item in enumerate(downloaded_files):
        print(f"{i + 1}. {item['title']} - {item['path']}")

    # 处理每个音频文件
    results = []
    for audio_path in audio_list:
        if os.path.exists(audio_path):
            print(f"\n开始处理: {audio_path}")
            output = audio_to_subtitle(audio_path, model=model, prompt=prompt, slice_length=slice_length)
            results.append({"audio": audio_path, "output": output})
            print(f"完成: {audio_path} -> {output}")
        else:
            print(f"文件不存在: {audio_path}")

    # 打印处理结果摘要
    if results:
        print("\n处理结果摘要:")
        for i, result in enumerate(results):
            print(f"{i + 1}. {result['audio']} -> {result['output']}")


if __name__ == "__main__":
    main()
