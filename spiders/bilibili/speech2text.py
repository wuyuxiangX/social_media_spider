import whisper
import os

whisper_model = None

def is_cuda_available():
    return whisper.torch.cuda.is_available()

def load_whisper(model="tiny"):
    global whisper_model
    whisper_model = whisper.load_model(model, device="cuda" if is_cuda_available() else "cpu")
    print("Whisper模型："+model)

def run_analysis(filename, model="tiny", prompt="以下是普通话的句子。", return_text=False, base_path=""):
    global whisper_model
    print("正在加载Whisper模型...")
    # 读取列表中的音频文件
    if base_path:
        audio_slice_dir = f"{base_path}/audio/slice/{filename}"
        outputs_dir = f"{base_path}/outputs"
    else:
        audio_slice_dir = f"audio/slice/{filename}"
        outputs_dir = "outputs"
    
    audio_list = os.listdir(audio_slice_dir)
    print("加载Whisper模型成功！")
    # 添加排序逻辑
    audio_files = sorted(
        audio_list,
        key=lambda x: int(os.path.splitext(x)[0])  # 按文件名数字排序
    )
    # 创建outputs文件夹
    os.makedirs(outputs_dir, exist_ok=True)
    print("正在转换文本...")

    audio_list.sort(key=lambda x: int(x.split(".")[0])) # 将 audio_list 按照切片序号排序

    i = 1
    full_text = ""  # 用于存储完整文本
    
    for fn in audio_files:
        print(f"正在转换第{i}/{len(audio_files)}个音频... {fn}")
        # 识别音频
        result = whisper_model.transcribe(f"{audio_slice_dir}/{fn}", initial_prompt=prompt)
        segment_text = "".join([i["text"] for i in result["segments"] if i is not None])
        print(segment_text)
        
        # 添加到完整文本
        full_text += segment_text + "\n"

        # 如果不是只返回文本，则写入文件
        if not return_text:
            with open(f"{outputs_dir}/{filename}.txt", "a", encoding="utf-8") as f:
                f.write(segment_text)
                f.write("\n")
        i += 1
    
    # 如果需要返回文本，则返回完整文本
    if return_text:
        return full_text