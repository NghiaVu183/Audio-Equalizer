import customtkinter
import numpy as np
import pygame
import wave
import scipy.signal as signal
import sounddevice as sd
from tkinter import messagebox
import os

pygame.mixer.init()

customtkinter.set_appearance_mode("light")
customtkinter.set_default_color_theme("blue")
customtkinter.deactivate_automatic_dpi_awareness()

app = customtkinter.CTk()  # create CTk window
app.title("Audio Equalizer")
app.iconbitmap('D:/Workspace/DSP/images/icon.ico')
app.geometry("1000x600")
app.resizable(False, False)

# Display frame
display = customtkinter.CTkFrame(master=app, width=900, height=220, corner_radius=10)
display.place(relx=0.5, rely=0.22, anchor="center")

# Audio list
def getFiles(folder_path):    
    audio_files = [f for f in os.listdir(folder_path) if f.endswith((".mp3", ".wav"))]
    if not audio_files:
        messagebox.showinfo("Error", "No Files Found")
    return audio_files

def getDuration(file_path):
    try:
        total_duration = pygame.mixer.Sound(file_path).get_length()
        minutes, seconds = divmod(int(total_duration), 60)
        duration.configure(text=f"{minutes:02}:{seconds:02}")
    except Exception as e:
        print(f"Error reading file duration: {e}")
        return "00:00"

def list_callback(choice):
    file_path = os.path.join('D:/Workspace/DSP/audio', choice)
    getDuration(file_path)


audio_files = getFiles(folder_path='D:/Workspace/DSP/audio')
list_var = customtkinter.StringVar(value="Select 1 audio file below")
list = customtkinter.CTkOptionMenu(app, values=audio_files,
                                        width=300,
                                        command=list_callback,
                                        variable=list_var)
list.grid(row = 0, column = 0, padx=(120,30), pady=(260,0))


# Pause button
isPlaying = False
isPaused = False

def updateTime():
    global isPlaying
    if isPlaying:
        # Kiểm tra xem nhạc có đang phát hay không
        if not pygame.mixer.music.get_busy():
            current.configure(text="00:00")
            time_slider.set(0)
            pause.configure(text="Play")
            isPlaying = False
            return

        # Lấy thời gian đã phát (tính bằng mili giây)
        elapsed_time_ms = pygame.mixer.music.get_pos() + pygame.mixer.music.get_busy()

        # Chuyển đổi mili giây thành giây
        elapsed_time_s = elapsed_time_ms // 1000

        # Định dạng thời gian thành MM:SS
        minutes, seconds = divmod(elapsed_time_s, 60)
        current_time_str = f"{minutes:02}:{seconds:02}"

        # Cập nhật label current
        current.configure(text=current_time_str)

        # Cập nhật vị trí slider
        slider_position = (elapsed_time_s / total_duration) * 100
        time_slider.set(slider_position)

    # Lặp lại sau 500ms
    app.after(500, updateTime)


def play_pause_func():
    global isPlaying, isPaused, total_duration

    # Đường dẫn tới file đã chọn
    selected_file = list_var.get()
    file_path = os.path.join('D:/Workspace/DSP/audio', selected_file)

    if not os.path.exists(file_path):
        messagebox.showerror("Error", "Selected file not found!")
        return

    if not isPlaying:
        if isPaused:
            # Tiếp tục phát nhạc từ vị trí tạm dừng
            pygame.mixer.music.unpause()
        else:
            # Nếu nhạc chưa phát, phát nhạc từ đầu
            try:
                pygame.mixer.music.load(file_path)  # Load file âm thanh
                pygame.mixer.music.play()  # Phát nhạc
                # Lấy tổng thời lượng bài hát
                total_duration = pygame.mixer.Sound(file_path).get_length()
                minutes, seconds = divmod(int(total_duration), 60)
                duration.configure(text=f"{minutes:02}:{seconds:02}")
            except Exception as e:
                messagebox.showerror("Error", f"Cannot play the file: {e}")
                return

        pause.configure(text="Pause")  # Đổi tên nút thành Pause
        isPlaying = True
        isPaused = False
        updateTime()
    else:
        # Nếu nhạc đang phát, tạm dừng phát nhạc
        pygame.mixer.music.pause()  # Tạm dừng
        pause.configure(text="Play")  # Đổi tên nút thành Play
        isPlaying = False
        isPaused = True

pause = customtkinter.CTkButton(master=app, width=50, text="Play", command=play_pause_func)
pause.grid(row = 0, column = 1, padx=10, pady=(260,0))


# Stop button
def stop_func():
    time_slider.set(0)
    current.configure(text="00:00")
    pygame.mixer.music.stop()

stop = customtkinter.CTkButton(master=app, width=30, text="Stop", command=stop_func)
stop.grid(row = 0, column = 3, padx=20, pady=(260,0))

# Mode list
def mode_callback(selected_mode):
    global audio_files, sample
    # Đồng bộ sliders với mode
    update_sliders(selected_mode)
    
    # Lấy giá trị từ sliders
    gains = [slider.get() for slider in sliders]
    
    # Áp dụng equalizer
    equalized_audio = equalize_audio(audio_data, sample_rate, gains)
    
    # Phát lại âm thanh đã xử lý
    play_equalized_audio(equalized_audio, sample_rate)


def update_sliders(mode):
    """Cập nhật giá trị của các slider theo chế độ."""
    global sliders

    # Lấy danh sách giá trị từ chế độ
    values = slider_modes.get(mode, [0] * 31)
    
    # Cập nhật từng slider
    for i, slider in enumerate(sliders):
        if i < len(values):
            slider.set(values[i])


def equalize_audio(audio_data, sample_rate, gains):
    """
    Áp dụng equalizer trên audio_data dựa vào sliders.
    - audio_data: Mảng âm thanh đầu vào (numpy array).
    - sample_rate: Tần số lấy mẫu.
    - gains: Giá trị tăng giảm (dB) cho mỗi dải tần số.

    Trả về:
    - audio_data_equalized: Dữ liệu âm thanh đã được áp dụng equalizer.
    """
    # Dải tần số tương ứng với 31 sliders
    global frequencies

    # Dữ liệu kết quả sau khi áp dụng equalizer
    audio_data_equalized = np.zeros_like(audio_data)

    # Áp dụng bộ lọc từng dải tần số
    for i, gain in enumerate(gains):
        # Tạo bộ lọc thông dải cho dải tần tương ứng
        f1 = frequencies[i]
        f2 = frequencies[i+1] if i+1 < len(frequencies) else frequencies[i]*1.5
        b, a = signal.iirfilter(2, [f1/(sample_rate/2), f2/(sample_rate/2)], 
                                btype='band', ftype='butter')
        
        # Lọc tín hiệu và nhân hệ số gain (chuyển từ dB sang tỷ lệ)
        filtered = signal.lfilter(b, a, audio_data)
        audio_data_equalized += filtered * (10 ** (gain / 20))
    
    # Chuẩn hóa dữ liệu để tránh vượt quá biên độ
    audio_data_equalized = np.clip(audio_data_equalized, -1.0, 1.0)
    return audio_data_equalized

def play_equalized_audio(audio_data, sample_rate):
    """
    Phát âm thanh đã được xử lý.
    - audio_data: Dữ liệu âm thanh (numpy array).
    - sample_rate: Tần số lấy mẫu.
    """
    if audio_data is not None:
        sd.stop()  # Dừng phát trước đó
        sd.play(audio_data, samplerate=sample_rate)

def slider_callback(index):
    global audio_data, sample_rate
    # Lấy giá trị từ sliders
    gains = [slider.get() for slider in sliders]
    
    # Áp dụng equalizer
    equalized_audio = equalize_audio(audio_data, sample_rate, gains)
    
    # Phát lại âm thanh đã xử lý
    play_equalized_audio(equalized_audio, sample_rate)

modes = ["Flat", "Rock", "Pop", "Bass", "Treble", "Vocal", "Classical",
         "Hip-hop", "Dance", "Jazz", "Powerfull", "MUU"]

slider_modes = {
    "Flat": [0] * 31,
    "Rock": [7, 7, 6, 6, 5, 5, 5, 3, 2, 1, 0, 0, -1, -1, -2, -3, -3, -4, -3, -3, -2, -1, 0, 2, 3, 4, 5, 5, 5, 5, 4],
    "Pop": [0, 0, 0, 0, 1, 1, 2, 3, 4, 4, 4, 3, 2, 1, 0, 0, 0, -1, -1, -2, -2, -2, -2, -1, -1, 0, 1, 0, -1, -1, -1],
    "Bass": [12, 12, 12, 12, 12, 12, 12, 12, 11, 10, 9, 8, 6, 5, 3, 1, -1, -3, -4, -5, -6, -7, -8, -9, -9, -10, -11, -11, -11, -11, -11],
    "Treble": [-12, -11, -10, -10, -10, -10, -9, -8, -7, -7, -7, -6, -6, -5, -5, -3, -2, 0, 3, 5, 6, 8, 9, 9, 10, 11, 12, 12, 12, 12, 12],
    "Vocal": [-8, -7, -6, -5, -5, -4, -3, -3, 0, 0, 2, 5, 6, 7, 7, 7, 7, 7, 7, 7, 7, 6, 4, 3, 2, 0, -2, -5, -5, -5, -5, -5, -7],
    "Classical": [-3, -2, -1, 0, 1, 1, 1, 2, 2, 3, 3, 2, 1, 0, -1, -2, -4, -6, -8, -8, -5, -3, -1, 0, 1, 2, 4, 3, 1, 0, -1],
    "Hip-hop": [4, 4, 4, 4, 3, 3, 2, 1, 1, 1, 0, 0, -1, -1, -2, -2, -3, -3, -2, -2, -1, 0, 1, 1, 2, 3, 3, 3, 4, 3, 2],
    "Dance": [6, 6, 6, 6, 6, 7, 6, 4, 2, 1, 1, 0, -1, -2, -2, -1, -1, 0, 1, 1, 2, 3, 2, 2, 1, 0, -1, -1, -2, -2, -2],
    "Jazz": [-3, -2, -2, 0, 2, 3, 1, -2, -6, -3, -1, 0, 1, 3, 6, 5, 4, 3, 2, 2, 1, 1, 0, 0, 0, 0, 0, 0, -1, -1, -1],
    "Powerfull": [9, 8, 8, 8, 8, 7, 7, 6, 4, 1, -1, -2, -3, -4, -4, -4, -4, -4, -3, -2, 0, 1, 3, 5, 6, 8, 8, 8, 8, 8, 8],
    "MUU": [-12, -3, 4, 12, 6, 3, 6, 12, 4, -3, -12, 12, 3, -5, -9, -11, -11, -9, -5, 3, 12, 12, 3, -5, -9, -11, -11, -9, -5, 3, 12]
}

mode_var = customtkinter.StringVar(value="Select 1 mode below")
mode = customtkinter.CTkOptionMenu(app, values=modes,
                                        width=150,
                                        command=mode_callback,
                                        variable=mode_var)
mode.grid(row = 0, column = 4, padx=30, pady=(260,0))


# Record button
isRecording = False
rec_data = []
def rec_func():
    global isRecording, rec_data
    if not isRecording:
        # Bắt đầu ghi âm
        isRecording = True
        rec_data = []
        alarm.configure(fg_color="#FF0000")  # Chuyển báo động sang màu đỏ
        
        # Sử dụng sounddevice để ghi âm
        sd.default.samplerate = 44100
        sd.default.channels = 2
        sd.InputStream(callback=audio_callback).start()
    else:
        # Dừng ghi âm
        isRecording = False
        alarm.configure(fg_color="#00FF00")  # Chuyển báo động sang màu xanh
        rec.configure(text="Rec")
        
        # Lưu dữ liệu thành file .wav
        save_recording()

def audio_callback(indata, frames, time, status):
    global rec_data
    if isRecording:
        rec_data.append(indata.copy())

def save_recording():
    """Lưu dữ liệu ghi âm vào file .wav."""
    if not rec_data:
        print("Không có dữ liệu ghi âm để lưu.")
        return

    # Chuyển dữ liệu thành mảng numpy
    audio_array = np.concatenate(rec_data, axis=0)

    # Ghi âm thanh thành file .wav
    output_path = "D:/Workspace/DSP/recorded.wav"
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(2)  # 2 kênh (stereo)
        wf.setsampwidth(2)  # Mỗi mẫu 2 byte
        wf.setframerate(44100)
        wf.writeframes((audio_array * 32767).astype(np.int16).tobytes())

    print(f"Ghi âm đã được lưu vào {output_path}")

rec = customtkinter.CTkButton(master=app, width=30, text="Rec", command=rec_func)
rec.grid(row = 0, column = 5, padx=10, pady=(260,0))

# Rec alarm
alarm = customtkinter.CTkButton(master=app, width=20, height=20, text="",
                                fg_color="#00FF00", state="disabled", corner_radius=10)
alarm.grid(row = 0, column = 6, pady=(260,0))


# Time frame
time_frame = customtkinter.CTkFrame(master=app, width=800, height=30, corner_radius=10)
time_frame.place(relx=0.5, rely=0.54, anchor="center")

current = customtkinter.CTkLabel(master=time_frame, text="00:00", fg_color="transparent", width=30)
current.grid(row=0, column=0, padx=(10, 5), pady=5)

time_slider = customtkinter.CTkSlider(master=time_frame, width=750, height=20, corner_radius=10,
                                      from_=0, to=100)
time_slider.grid(row=0, column=1, padx=(5, 5), pady=5)
time_slider.set(0)

duration = customtkinter.CTkLabel(master=time_frame, text="00:00", fg_color="transparent", width=30)
duration.grid(row=0, column=2, padx=(5, 10), pady=5)


# Frequency sliders
slider_frame = customtkinter.CTkFrame(master=app, width=899, height=220, corner_radius=10)
slider_frame.place(relx=0.5, rely = 0.79, anchor="center")
frequencies = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
               800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
               12500, 16000, 20000]

labels = ["20", "25", "31.5", "40", "50", "63", "80", "100", "125", "160", "200", "250",
              "315", "400", "500", "630", "800", "1K", "1.25K", "1.6K", "2K", "2.5K", "3.15K",
              "4K", "5K", "6.3K", "8K", "10K", "12.5K", "16K", "20K"]

sliders = []

for i, freq in enumerate(frequencies):
    slider = customtkinter.CTkSlider(master=slider_frame, width=20, height=200,
                                     orientation="vertical",
                                     from_=-12, to=12)
    slider.grid(row=0, column=i, padx=4)
    sliders.append(slider)
    label = customtkinter.CTkLabel(master=slider_frame, text=labels[i], fg_color="transparent")
    label.grid(row=1, column=i,padx=4)
    labels.append(label)

    slider.configure(command=lambda value, index=i: slider_callback(index, value))

app.mainloop()