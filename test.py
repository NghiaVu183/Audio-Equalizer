import customtkinter
import numpy as np
import pygame
import wave
import scipy.signal as signal
import sounddevice as sd
from tkinter import messagebox
import os
from pydub import AudioSegment

pygame.mixer.init()

customtkinter.set_appearance_mode("light")
customtkinter.set_default_color_theme("blue")
customtkinter.deactivate_automatic_dpi_awareness()

app = customtkinter.CTk()  # create CTk window
app.title("Audio Equalizer")
app.iconbitmap('D:/Workspace/DSP/Audio-Equalizer/images/icon.ico')
app.geometry("1000x600")
app.resizable(False, False)

# Display frame
display = customtkinter.CTkFrame(master=app, width=900, height=220, corner_radius=10)
display.place(relx=0.5, rely=0.22, anchor="center")

# EQ xử lý tín hiệu theo thời gian thực
def apply_eq(audio_data, fs):
    """Áp dụng EQ với bộ lọc bandpass và gain từ sliders."""
    global sliders, frequencies
    processed_data = np.zeros_like(audio_data)
    for i, freq in enumerate(frequencies):
        # Tính toán tần số cắt
        lowcut = max(0, freq / np.sqrt(2))
        highcut = min(fs / 2, freq * np.sqrt(2))
        
        # Kiểm tra nếu lowcut và highcut hợp lệ
        if lowcut <= 0 or highcut >= fs / 2 or lowcut >= highcut:
            continue  # Bỏ qua bộ lọc không hợp lệ

        gain = sliders[i].get()

        # Tạo bộ lọc thông dải
        sos = signal.butter(2, [lowcut / (fs / 2), highcut / (fs / 2)], btype='band', output='sos')
        filtered = signal.sosfilt(sos, audio_data)

        # Áp dụng gain
        processed_data += filtered * (10 ** (gain / 20))  # Chuyển đổi từ dB sang tỷ lệ tuyến tính
    return processed_data


current_position = 0  # Thời gian hiện tại của âm thanh (ms)
stream = None

def apply_eq_realtime():
    """Xử lý và phát lại âm thanh theo EQ trong thời gian thực."""
    global list_var, current_position, isPlaying, stream

    selected_file = list_var.get()
    file_path = os.path.join('D:/Workspace/DSP/Audio-Equalizer/audio', selected_file)

    if not os.path.exists(file_path):
        messagebox.showerror("Error", "File not found!")
        return

    # Tạm dừng nhạc và lấy vị trí hiện tại
    if isPlaying:
        pygame.mixer.music.pause()
        current_position = pygame.mixer.music.get_pos()

    # Đọc file âm thanh
    audio = AudioSegment.from_file(file_path)
    audio = audio.set_frame_rate(44100).set_channels(1)  # Đảm bảo mono để xử lý dễ dàng
    audio_array = np.array(audio.get_array_of_samples(), dtype=np.float32)
    audio_array = audio_array / 32768.0  # Chuyển đổi về [-1, 1]

    # Áp dụng EQ
    fs = audio.frame_rate
    processed_audio = apply_eq(audio_array, fs)

    # Phát lại tín hiệu từ vị trí hiện tại
    start_sample = int((current_position / 1000) * fs)
    playback_audio = processed_audio[start_sample:]

    # Dừng luồng âm thanh hiện tại (nếu có)
    if stream and stream.active:
        stream.stop()
        stream.close()

    # Chạy phát lại bằng sounddevice
    def callback(outdata, frames, time, status):
        nonlocal playback_audio
        if len(playback_audio) < frames:
            outdata[:len(playback_audio)] = playback_audio[:, np.newaxis]
            outdata[len(playback_audio):] = 0
            playback_audio = np.array([])  # Hết dữ liệu
        else:
            outdata[:] = playback_audio[:frames, np.newaxis]
            playback_audio = playback_audio[frames:]

    # Tạo luồng âm thanh mới
    stream = sd.OutputStream(samplerate=fs, channels=1, callback=callback)
    stream.start()


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
    file_path = os.path.join('D:/Workspace/DSP/Audio-Equalizer/audio', choice)
    getDuration(file_path)


audio_files = getFiles(folder_path='D:/Workspace/DSP/Audio-Equalizer/audio')
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
    file_path = os.path.join('D:/Workspace/DSP/Audio-Equalizer/audio', selected_file)

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
def update_sliders(mode):
    """Cập nhật giá trị của các slider theo chế độ."""
    global sliders

    # Lấy danh sách giá trị từ chế độ
    values = slider_modes.get(mode, [0] * 31)
    
    # Cập nhật từng slider
    for i, slider in enumerate(sliders):
        if i < len(values):
            slider.set(values[i])


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

def mode_callback(selected_mode):
    """Đồng bộ sliders với chế độ và áp dụng EQ."""
    update_sliders(selected_mode)  # Cập nhật sliders theo mode
    apply_eq_realtime()  # Áp dụng EQ ngay lập tức

mode_var = customtkinter.StringVar(value="Select 1 mode below")
mode = customtkinter.CTkOptionMenu(app, values=modes,
                                        width=150,
                                        command=mode_callback,
                                        variable=mode_var)
mode.grid(row = 0, column = 4, padx=30, pady=(260,0))

# Kết nối callback mode với menu
mode.configure(command=mode_callback)

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
    output_path = "D:/Workspace/DSP/Audio-Equalizer/recorded.wav"
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

app.mainloop()