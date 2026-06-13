# -*- coding: utf-8 -*-
"""
============================================================
文件名: player.py
功能描述: GTP播放器高级封装类 - 整合解析/渲染/音频/时间线的完整流程

原理:
  将 GTP 文件的完整生命周期（加载→解析→渲染→音频初始化→播放控制→时间线）
  封装为单一的高层 API 类 GTPPlayer，
  使主程序只需调用简单方法即可实现完整的 GTP 播放功能。

核心职责:
  1. 文件加载与解析 (parse_gtp)
  2. 音轨渲染 (TabRenderer.render_from_file)
  3. 音频引擎管理 (SynthEngine + MidiConverter)
  4. 播放光标时间线构建 (time_ms ↔ scroll_y 映射)
  5. 时间↔位置双向转换 (二分查找+线性插值)

设计原则:
  - 高内聚低耦合: 所有GTP相关逻辑集中在此类中
  - 最小化依赖: 仅依赖 gtp_engine 内部模块和 PyQt5
  - 线程安全: 音频操作在独立线程中执行
  - 优雅降级: 缺少依赖时提供有意义的错误信息

使用示例:
    from gtp_engine.player import GTPPlayer
    
    # 创建播放器实例
    player = GTPPlayer()
    
    # 加载并渲染
    player.load("song.gp5")
    images = player.render_track(0)  # 渲染第1轨
    
    # 初始化音频（可选）
    if player.init_audio():
        player.play()
    
    # 获取时间线数据（用于播放光标）
    timeline = player.build_timeline(page_layouts, images, display_width)
    
    # 时间↔位置转换
    scroll_y = player.time_to_scroll_pos(5000)  # 5000ms → 像素位置
    time_ms = player.scroll_pos_to_time(scroll_y)  # 像素位置 → ms
    
    # 清理资源
    player.shutdown()

依赖库:
  - gtp_engine.parser (parse_gtp, GTPParser)
  - gtp_engine.renderer (TabRenderer, RenderConfig)
  - gtp_engine.audio (MidiConverter, SynthEngine)
  - gtp_engine.models (GTPSong, GTPTrack)
  - PyQt5 (QPixmap, 用于图像渲染)

创建日期: 2026-06-12
最后更新: 2026-06-12 (v0.2.0 - Phase 4 库化重构)
============================================================
"""

import bisect
from typing import List, Optional, Tuple, Dict, Callable

from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont

# 内部模块导入
from .parser import parse_gtp, GTPParser
from .renderer import TabRenderer
from .utils import RenderConfig
from .audio import MidiConverter, MidiEvent, SynthEngine
from .models import GTPSong, GTPTrack


class GTPPlayer:
    """
    GTP文件播放器 - 高级封装类
    
    功能概述:
      提供 Guitar Pro 文件的完整播放解决方案，包括:
      - 文件解析与元数据提取
      - 六线谱渲染为 QPixmap 图像
      - FluidSynth 音频合成与播放
      - 播放光标时间线构建
      - 时间↔位置双向映射
      
    设计模式:
      - 门面模式(Facade): 将多个子系统的复杂操作封装为简单接口
      - 状态模式(State): 管理加载/就绪/播放/暂停等状态转换
    
    参数说明(初始化):
      gain: 主音量(0.0-1.0), 调整效果: 1.0=最大音量, 0.7=推荐默认值
      sample_rate: 采样率(Hz), 调整效果: 44100=CD音质, 48000=高清
      buffer_size: 缓冲区大小, 调整效果: 256=低延迟, 512=稳定
    """
    
    # ===== 音频模式常量 =====
    MODE_ALL = "all"           # 全轨并轨模式
    MODE_CURRENT = "current"   # 仅当前轨模式
    MODE_OFF = "off"           # 关闭音频模式
    
    def __init__(self, gain: float = 0.7, sample_rate: int = 44100, buffer_size: int = 512):
        """
        初始化 GTP 播放器
        
        参数:
            gain:         主音量增益(0.0-1.0), 调整效果: 0.7=适中音量
            sample_rate:  音频采样率(Hz), 调整效果: 44100=CD标准
            buffer_size:  音频缓冲区大小, 调整效果: 512=平衡延迟与稳定性
        """
        # ===== 核心组件 =====
        self._parser = GTPParser()           # 解析器
        self._renderer = TabRenderer()       # 渲染器
        self._midi_converter = MidiConverter()  # MIDI转换器
        self._synth_engine: Optional[SynthEngine] = None  # 音频合成器(延迟初始化)
        
        # ===== 数据状态 =====
        self._song: Optional[GTPSong] = None      # 当前加载的歌曲对象
        self._file_path: str = ""                  # 当前文件路径
        self._current_track: int = 0               # 当前选中的音轨索引
        
        # ===== 音频状态 =====
        self._audio_mode: str = self.MODE_ALL      # 当前音频模式
        self._audio_enabled: bool = True           # 是否启用音频
        self._audio_events: List[MidiEvent] = []   # 当前MIDI事件列表
        self._track_channels: List[int] = []       # 通道映射(全轨模式)
        
        # ===== 时间线数据 =====
        self._playhead_timeline: List[dict] = []   # 播放光标时间线索引
        self._timeline_times: List[float] = []     # 预提取的时间排序列表(性能优化)
        self._timeline_scroll_ys: List[float] = [] # 预提取的scroll_y排序列表
        self._total_audio_duration_ms: float = 0.0 # 总音频时长(ms)
        
        # ===== 音频参数 =====
        self._gain = gain
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        
        # ===== 回调函数 =====
        self._note_callback: Optional[Callable] = None  # 音符触发回调
    
    # ================================================================
    # 属性访问器
    # ================================================================
    
    @property
    def song(self) -> Optional[GTPSong]:
        """当前加载的GTP歌曲对象"""
        return self._song
    
    @property
    def file_path(self) -> str:
        """当前GTP文件路径"""
        return self._file_path
    
    @property
    def current_track(self) -> int:
        """当前选中的音轨索引"""
        return self._current_track
    
    @current_track.setter
    def current_track(self, value: int) -> None:
        """设置当前音轨索引"""
        self._current_track = value
    
    @property
    def audio_mode(self) -> str:
        """当前音频模式 (all/current/off)"""
        return self._audio_mode
    
    @property
    def is_audio_ready(self) -> bool:
        """音频引擎是否已初始化且可用"""
        return self._synth_engine is not None and self._synth_engine.is_initialized

    @property
    def is_loaded(self) -> bool:
        """是否已加载GTP文件(用于导出时判断是否有谱面内容)"""
        return hasattr(self, '_song') and self._song is not None

    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._synth_engine is not None and self._synth_engine.is_playing
    
    @property
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._synth_engine is not None and self._synth_engine.is_paused
    
    @property
    def current_time_ms(self) -> float:
        """当前音频播放时间(毫秒)"""
        if self._synth_engine:
            return self._synth_engine.current_time_ms
        return 0.0
    
    @property
    def total_duration_ms(self) -> float:
        """总音频时长(毫秒)"""
        return self._total_audio_duration_ms
    
    @property
    def playhead_timeline(self) -> List[dict]:
        """播放光标时间线数据"""
        return self._playhead_timeline
    
    @property
    def track_count(self) -> int:
        """当前文件的音轨数量"""
        if self._song:
            return len(self._song.tracks)
        return 0
    
    @property
    def tracks(self) -> List[GTPTrack]:
        """获取所有音轨列表"""
        if self._song:
            return self._song.tracks
        return []
    
    # ================================================================
    # 文件加载与解析
    # ================================================================
    
    def load(self, file_path: str) -> GTPSong:
        """
        加载并解析 Guitar Pro 文件
        
        参数:
            file_path: .gp3/.gp4/.gp5/.gpx 文件路径
            
        返回:
            GTPSong 歌曲对象
            
        异常:
            GPException: 文件格式错误或无法解析时抛出
            ImportError: 缺少 pyguitarpro 依赖时抛出
            FileNotFoundError: 文件不存在时抛出
            
        示例:
            >>> player = GTPPlayer()
            >>> song = player.load("my_song.gp5")
            >>> print(f"标题: {song.title}, 音轨数: {player.track_count}")
        """
        self._file_path = file_path
        self._song = parse_gtp(file_path)
        self._current_track = 0
        return self._song
    
    def get_track_info(self, track_index: int = None) -> Dict:
        """
        获取指定音轨的详细信息
        
        参数:
            track_index: 音轨索引，None则使用当前音轨
            
        返回:
            包含音轨信息的字典:
            {
                'index': 音轨索引,
                'name': 音轨名称,
                'tuning': 调弦元组(MIDI音高),
                'tuning_name': 调弦名称,
                'fret_count': 品格数,
                'measure_count': 小节数,
                'instrument': MIDI乐器编号,
                'is_visible': 是否可见,
            }
            
        异常:
            IndexError: 音轨索引超出范围时抛出
        """
        if not self._song:
            raise ValueError("尚未加载任何文件，请先调用 load()")
        
        idx = track_index if track_index is not None else self._current_track
        if idx >= len(self._song.tracks):
            raise IndexError(f"音轨索引{idx}超出范围(0-{len(self._song.tracks)-1})")
        
        track = self._song.tracks[idx]
        
        return {
            'index': idx,
            'name': track.name or f"音轨{idx + 1}",
            'tuning': track.strings,
            'tuning_name': track.get_tuning_name(),
            'fret_count': track.fret_count,
            'measure_count': len(track.measures),
            'instrument': track.instrument,
            'is_visible': track.is_visible,
        }
    
    def get_all_tracks_info(self) -> List[Dict]:
        """
        获取所有音轨的信息列表
        
        返回:
            字典列表，每个元素包含一个音轨的详细信息
            (格式同 get_track_info 的返回值)
        """
        if not self._song:
            return []
        
        return [self.get_track_info(i) for i in range(len(self._song.tracks))]
    
    # ================================================================
    # 渲染功能
    # ================================================================
    
    def render_track(self, track_index: int = None, 
                     config: RenderConfig = None) -> List[QPixmap]:
        """
        渲染指定音轨的六线谱图像
        
        参数:
            track_index: 要渲染的音轨索引，None则使用当前音轨
            config:      自定义渲染配置，None则使用默认配置
            
        返回:
            QPixmap列表，每元素对应一页乐谱图像
            
        注意:
            同时会更新 last_layouts 属性，可用于播放光标等功能。
            如果尚未加载文件，会自动调用 load()。
            
        示例:
            >>> pages = player.render_track(0)
            >>> print(f"共{len(pages)}页")
            >>> pages[0].save("page1.png", "PNG")
        """
        if not self._file_path:
            raise ValueError("尚未加载文件，请先调用 load()")
        
        idx = track_index if track_index is not None else self._current_track
        
        if config:
            self._renderer = TabRenderer(config)
        
        pixmaps = self._renderer.render_from_file(self._file_path, track_index=idx)
        
        # 更新当前音轨索引
        self._current_track = idx
        
        return pixmaps
    
    def render_from_song(self, song: GTPSong = None, 
                         track_index: int = None,
                         config: RenderConfig = None) -> List[QPixmap]:
        """
        从已有的 GTPSong 对象渲染（不重新解析文件）
        
        参数:
            song:        GTPSong 对象，None则使用已加载的song
            track_index:  音轨索引
            config:      渲染配置
            
        返回:
            QPixmap列表
        """
        target_song = song or self._song
        if not target_song:
            raise ValueError("没有可用的歌曲数据")
        
        idx = track_index if track_index is not None else self._current_track
        
        if config:
            renderer = TabRenderer(config)
            return renderer.render(target_song, track_index=idx)
        else:
            return self._renderer.render(target_song, track_index=idx)
    
    @property
    def last_layouts(self) -> list:
        """
        获取上次渲染的布局数据
        
        返回:
            List[PageLayout], 由 TabRenderer.render() 生成，
            包含每页/行/小节/拍的精确坐标信息
        """
        return getattr(self._renderer, 'last_layouts', [])
    
    # ================================================================
    # 音频引擎管理
    # ================================================================
    
    def init_audio(self, note_callback: Callable = None) -> bool:
        """
        初始化音频播放引擎
        
        功能:
          1. 创建 SynthEngine 实例（FluidSynth 合成器）
          2. 初始化音频输出驱动
          3. 自动搜索并加载 SoundFont 音色文件
          4. 设置音符回调（用于视觉高亮同步）
          5. 根据 audio_mode 转换并加载 MIDI 事件
          
        参数:
            note_callback: 音符触发回调函数，签名为 (midi_pitch, velocity, time_ms) → None
                          用于在UI中高亮当前发声的音符
                          
        返回:
            True 表示初始化成功，False 表示失败（缺少依赖或SoundFont）
            
        注意:
          此方法应在 load() 之后调用。
          失败时不会抛出异常，而是返回 False 并打印警告信息。
          
        错误处理:
          - ImportError(pyfluidsynth未安装): 返回False，提示安装
          - SoundFont未找到: 返回False，提示放置sf2文件
          - 初始化失败: 返回False，打印详细错误
        """
        if not self._song:
            print("[GTPPlayer] 错误: 尚未加载文件，请先调用 load()")
            return False
        
        try:
            # === Step 1: 创建 FluidSynth 合成器 ===
            self._synth_engine = SynthEngine(
                gain=self._gain,
                sample_rate=self._sample_rate,
                buffer_size=self._buffer_size
            )
            
            # === Step 2: 初始化音频驱动 ===
            if not self._synth_engine.initialize():
                print("[GTPPlayer] 错误: FluidSynth 初始化失败")
                print("  可能原因: fluidsynth 库未正确安装或音频设备不可用")
                print("  解决方案:")
                print("    Windows: 下载 libfluidsynth-3.dll 放到项目目录")
                print("    Linux:   sudo apt-get install fluidsynth")
                return False
            
            # === Step 3: 加载 SoundFont ===
            sf_path = self._synth_engine.load_soundfont()
            if not sf_path:
                print("[GTPPlayer] 警告: 未找到 SoundFont 文件")
                print("  将使用默认音色（可能效果不佳）")
                print("  建议: 下载 FluidR3_GM.sf2 放到 ./soundfont/ 目录")
            else:
                print(f"[GTPPlayer] ✓ 已加载 SoundFont: {sf_path}")
            
            # === Step 4: 设置音符回调 ===
            self._note_callback = note_callback
            if note_callback:
                self._synth_engine.set_note_callback(note_callback)
            
            # === Step 5: 转换并加载 MIDI 事件 ===
            self.rebuild_audio_events()
            
            # 打印就绪信息
            mode_label = "全轨并轨" if self._audio_mode == self.MODE_ALL else f"仅当前轨"
            duration_ms = self.get_current_duration_ms()
            print(f"[GTPPlayer] ✓ 引擎就绪[{mode_label}]: "
                  f"{len(self._audio_events)}个MIDI事件, "
                  f"{len(self._track_channels)}个通道, "
                  f"BPM={self._song.tempo}, "
                  f"时长={duration_ms / 1000:.1f}秒")
            
            return True
            
        except ImportError as e:
            print(f"[GTPPlayer] 错误: 依赖库缺失 - {e}")
            print("  请安装: pip install pyfluidsynth")
            return False
        except Exception as e:
            print(f"[GTPPlayer] 错误: 音频初始化失败 - {e}")
            return False
    
    def get_current_duration_ms(self) -> float:
        """
        获取当前模式的音频总时长(ms)
        
        返回:
          全轨模式: 所有轨道的最长时长
          单轨模式: 当前轨道的时长
        """
        if not self._song or not self._midi_converter:
            return 0.0
        
        if self._audio_mode == self.MODE_ALL:
            return self._midi_converter.get_all_tracks_duration_ms(self._song)
        else:
            return self._midi_converter.get_total_duration_ms(
                self._song, self._current_track
            )
    
    def set_audio_mode(self, mode: str) -> None:
        """
        切换音频播放模式
        
        参数:
            mode: 目标模式
              - "all"(MODE_ALL):     全轨并轨 - 所有音轨同时播放(默认)
              - "current"(MODE_CURRENT): 仅当前轨 - 只播放当前选中音轨
              - "off"(MODE_OFF):     关闭音频 - 仅滚动播放，不输出声音
              
        原理:
          切换模式时会自动停止当前播放、重建MIDI事件序列、重新加载到合成器。
          如果引擎未初始化，仅更新模式标记（待后续 init_audio() 时生效）。
        """
        if self._audio_mode == mode:
            return  # 模式未变，跳过
        
        old_mode = self._audio_mode
        self._audio_mode = mode
        
        # 更新启用状态
        self._audio_enabled = (mode != self.MODE_OFF)
        
        # 如果是关闭模式，立即停止音频
        if mode == self.MODE_OFF and self._synth_engine:
            self._synth_engine.stop()
        
        # 如果引擎已初始化，根据新模式重建事件
        if self._synth_engine and mode != self.MODE_OFF:
            self.rebuild_audio_events()
        
        print(f"[GTPPlayer] 音频模式: {old_mode} → {mode}")
    
    def rebuild_audio_events(self) -> None:
        """
        重新构建 MIDI 事件序列（切换音轨/切换音频模式时调用）
        
        功能:
          根据 audio_mode 决定转换范围:
          - 全轨模式: 转换所有音轨，每轨独立 MIDI 通道
          - 单轨模式: 仅转换当前选中音轨
          
        流程:
          1. 停止当前播放（如有）
          2. 根据模式选择转换方式
          3. 为各通道设置乐器音色（吉他/鼓组）
          4. 重新加载事件到合成器
        """
        if not self._song or not self._midi_converter or not self._synth_engine:
            return
        
        # 先停止正在播放的音频
        self._synth_engine.stop()
        
        # === 根据模式选择转换方式 ===
        if self._audio_mode == self.MODE_ALL:
            # 全轨并轨: 转换所有音轨
            self._audio_events, self._track_channels = (
                self._midi_converter.convert_all_tracks(self._song)
            )
            
            # 为每个通道设置合适的乐器音色
            if self._track_channels:
                for ch in set(self._track_channels):
                    if ch == 9:
                        # 通道9是MIDI打击乐保留通道，设置为鼓组
                        try:
                            self._synth_engine.set_drum_kit(ch, kit=0)
                        except Exception:
                            pass
                    else:
                        # 其他通道设置为电吉他音色
                        try:
                            # 27 = Clean Electric Guitar (MIDI程序号)
                            self._synth_engine.set_instrument(ch, 27)
                        except Exception:
                            pass
        else:
            # 仅当前轨: 只转换当前选中的音轨
            self._track_channels = []
            self._audio_events = self._midi_converter.convert(
                self._song, track_index=self._current_track
            )
        
        # 重新加载到合成器
        if self._audio_events:
            self._synth_engine.load_events(
                self._audio_events,
                bpm=self._song.tempo,
                ticks_per_beat=480  # MIDI标准分辨率
            )
            
            # 打印日志
            mode_label = ("全轨并轨" if self._audio_mode == self.MODE_ALL 
                         else f"仅当前轨(#{self._current_track + 1})")
            print(f"[GTPPlayer] 事件重建[{mode_label}]: "
                  f"{len(self._audio_events)}个事件, "
                  f"{len(self._track_channels)}个通道")
    
    # ================================================================
    # 播放控制
    # ================================================================
    
    def play(self) -> None:
        """
        开始播放音频
        
        注意: 需要先调用 init_audio() 初始化引擎
        """
        if self._synth_engine and self._audio_enabled:
            self._synth_engine.play()
    
    def pause(self) -> None:
        """
        暂停播放（保持当前位置，可恢复）
        """
        if self._synth_engine:
            self._synth_engine.pause()
    
    def resume(self) -> None:
        """
        恢复播放（从暂停位置继续）
        """
        if self._synth_engine:
            self._synth_engine.resume()
    
    def stop(self) -> None:
        """
        停止播放（回到开头）
        """
        if self._synth_engine:
            self._synth_engine.stop()
    
    def seek(self, time_ms: float) -> None:
        """
        跳转到指定时间位置
        
        参数:
            time_ms: 目标时间(毫秒)，0=开头
        """
        if self._synth_engine:
            self._synth_engine.seek(time_ms)
    
    def shutdown(self) -> None:
        """
        完全关闭音频引擎并释放所有资源
        
        应在程序退出前调用，确保:
        - 停止播放线程
        - 释放音频设备
        - 释放合成器内存
        """
        if self._synth_engine:
            try:
                self._synth_engine.stop()
                self._synth_engine.shutdown()
            except Exception:
                pass
            finally:
                self._synth_engine = None
    
    # ================================================================
    # 播放光标时间线
    # ================================================================
    
    def build_timeline(self, page_layouts: list, images: List[QPixmap], 
                       display_width: int) -> List[dict]:
        """
        构建播放光标时间线 - 将每个拍映射到其音频时间和屏幕位置
        
        原理:
          遍历所有页面的布局数据(PageLayout→SystemLayout→MeasureLayout→BeatLayout)，
          结合 GTP 歌曲的 BPM 和时间签名，计算每个拍对应的音频时间位置(ms)，
          生成一个按时间排序的时间线索引。
          
        核心改进:
          每个拍同时记录 scroll_y（在总内容中的Y偏移），
          使滚动位置可以由音乐时间驱动，而非线性恒速滚动。
          这样在音符密集区(16/32分音符)播放条自动加快，
          在稀疏区(全/二分音符)自动减慢，与实际音乐节奏同步。
          
        参数:
            page_layouts: TabRenderer 生成的布局数据(List[PageLayout])
            images:       渲染后的页面图像列表(List[QPixmap])
            display_width: 显示区域宽度(px)，用于计算缩放比例
            
        返回:
          List[dict], 每个元素包含:
            - time_ms:   该拍的起始音频时间(毫秒)
            - scroll_y:  该拍在总内容中的Y位置(像素)
            - page_idx:  所在页面索引
            - sys_idx:   所在系统(行)索引
            - meas_idx:  所在小节索引
            - beat_idx:  该小节内的拍索引
            - x_center:  该拍的中心X坐标
            - x_start:   该拍的起始X坐标
            - x_end:     该拍的结束X坐标
            - y_top:     系统顶部Y坐标
            - y_bottom:  系统底部Y坐标
            
        性能优化:
          - 预提取 _timeline_times 和 _timeline_scroll_ys 排序列表
          - 后续 _update_playhead/time_to_scroll_pos 直接复用，避免每帧O(n)分配
        """
        self._playhead_timeline = []
        self._timeline_times = []
        self._timeline_scroll_ys = []
        
        if not page_layouts or not self._song:
            return self._playhead_timeline
        
        # 获取BPM(取第一个tempo标记, 默认120)
        bpm = 120
        if hasattr(self._song, 'tempo_changes') and self._song.tempo_changes:
            bpm = self._song.tempo_changes[0].value
            if bpm <= 0:
                bpm = 120
        elif hasattr(self._song, 'tempo') and self._song.tempo > 0:
            bpm = self._song.tempo
        
        # MIDI 时间参数
        ticks_per_beat = 480  # MIDI 标准分辨率
        ms_per_tick = 60000.0 / (bpm * ticks_per_beat)
        
        current_time_ticks = 0
        current_time_ms = 0.0

        # 计算每页的缩放高度和缩放比(用于累计scroll_y，与paintEvent一致)
        draw_w = display_width - 20  # 减去左右边距
        page_heights = []  # 每页缩放后的高度
        page_scales = []   # 每页的缩放比(width_ratio)
        
        for img in images:
            if img and not img.isNull():
                ratio = draw_w / img.width() if img.width() > 0 else 1
                page_heights.append(img.height() * ratio + 5)
                page_scales.append(ratio)
            else:
                page_heights.append(0)
                page_scales.append(1)
        
        cumulative_y = 0.0  # 累计Y偏移(所有之前页面的总高度)
        
        # 遍历所有页面布局
        for page_idx, page in enumerate(page_layouts):
            page_base_y = cumulative_y  # 当前页的起始Y
            page_scale_ratio = page_scales[page_idx] if page_idx < len(page_scales) else 1
            
            if page_idx < len(page_heights):
                cumulative_y += page_heights[page_idx]
            
            # 遍历该页的所有系统(行)
            for sys_idx, system in enumerate(page.systems):
                # 遍历该系统的所有小节
                for meas_idx, m_layout in enumerate(system.measures):
                    measure = m_layout.measure
                    
                    # 获取该小节的拍号信息
                    if hasattr(measure, 'time_signature'):
                        ts = measure.time_signature
                        numerator = getattr(ts, 'numerator', 4)
                        denominator = getattr(ts, 'denominator', 4)
                    else:
                        numerator, denominator = 4, 4
                    
                    # 计算该小节的总tick数
                    measure_ticks = int(numerator * ticks_per_beat * 4 / max(denominator, 1))
                    
                    beats_in_measure = m_layout.beats
                    if not beats_in_measure:
                        # 无拍的空小节：只累加时间
                        current_time_ticks += measure_ticks
                        current_time_ms = current_time_ticks * ms_per_tick
                        continue
                    
                    n_beats = len(beats_in_measure)
                    tick_per_beat = measure_ticks // max(n_beats, 1)
                    
                    # 遍历该小节的所有拍
                    for beat_idx, b_layout in enumerate(beats_in_measure):
                        # === 计算 scroll_y: 每个拍有独立递增的Y位置 ===
                        sys_beats_count = sum(len(m.beats) for m in system.measures)
                        beats_before = (
                            sum(len(m2.beats) for m2 in system.measures[:meas_idx]) 
                            + beat_idx
                        )
                        rel_pos = beats_before / max(sys_beats_count, 1)
                        sys_h_render = max(system.y_tab_bottom - system.y_tab_top, 1)

                        scroll_y = (
                            page_base_y
                            + (system.y_tab_top + rel_pos * sys_h_render) * page_scale_ratio
                        )
                        
                        # 构建时间线索引条目
                        entry = {
                            'time_ms': current_time_ms,
                            'scroll_y': scroll_y,
                            'page_idx': page_idx,
                            'sys_idx': sys_idx,
                            'meas_idx': meas_idx,
                            'beat_idx': beat_idx,
                            'x_center': b_layout.x_center,
                            'x_start': b_layout.x_start,
                            'x_end': b_layout.x_end,
                            'y_top': system.y_tab_top,
                            'y_bottom': system.y_tab_bottom,
                        }
                        self._playhead_timeline.append(entry)
                        
                        # 累加时间和tick
                        current_time_ticks += tick_per_beat
                        current_time_ms = current_time_ticks * ms_per_tick
        
        # === 后处理: 确保scroll_y严格单调递增 + 可选哨兵 ===
        if self._playhead_timeline:
            # 强制单调递增(防止布局数据异常导致回退)
            prev_y = -1.0
            for entry in self._playhead_timeline:
                if entry['scroll_y'] <= prev_y:
                    entry['scroll_y'] = prev_y + 0.5  # 最小增量保证递增
                prev_y = entry['scroll_y']
            
            # 更新总时长
            self._total_audio_duration_ms = self._playhead_timeline[-1]['time_ms']

            # 总内容高度(与 _calculate_total_distance 一致)
            total_content_h = max(cumulative_y - 5, 0)
            
            last_entry = self._playhead_timeline[-1]
            last_scroll_y = last_entry['scroll_y']
            last_time_ms = last_entry['time_ms']
            remaining_h = total_content_h - last_scroll_y

            # 仅当剩余空白区域超过50px时才添加哨兵点
            if remaining_h > 50:
                first = self._playhead_timeline[0]
                elapsed_y = last_scroll_y - first['scroll_y']
                elapsed_t = max(last_time_ms - first['time_ms'], 1)
                avg_speed = elapsed_y / elapsed_t
                estimated_remaining_ms = remaining_h / max(avg_speed, 0.01)

                sentinel = {
                    'time_ms': last_time_ms + estimated_remaining_ms,
                    'scroll_y': float(total_content_h),
                    'page_idx': len(page_layouts) - 1,
                    'sys_idx': 0, 'meas_idx': 0, 'beat_idx': 0,
                    'x_center': 0, 'x_start': 0, 'x_end': 0,
                    'y_top': 0, 'y_bottom': 0,
                }
                self._playhead_timeline.append(sentinel)
                self._total_audio_duration_ms = sentinel['time_ms']

            # === 性能优化: 预提取bisect关键排序列表 ===
            self._timeline_times = [e['time_ms'] for e in self._playhead_timeline]
            self._timeline_scroll_ys = [e['scroll_y'] for e in self._playhead_timeline]
        else:
            self._total_audio_duration_ms = 0.0
            self._timeline_times = []
            self._timeline_scroll_ys = []
        
        return self._playhead_timeline
    
    # ================================================================
    # 时间 ↔ 位置 双向映射
    # ================================================================
    
    def update_playhead(self, time_ms: float = None) -> Optional[tuple]:
        """
        根据当前播放时间更新光标位置
        
        参数:
            time_ms: 当前音频时间(毫秒)。None则从 synth_engine 获取。
            
        返回:
          光标信息元组或None:
          (page_idx, sys_idx, meas_idx, beat_idx, x_in_page, progress_in_beat)
          - progress_in_beat ∈ [0,1) 表示当前拍内的进度
          - beat_idx=-1 表示还未到第一个拍
        """
        if not self._playhead_timeline:
            return None
        
        # 获取当前时间
        if time_ms is None and self._synth_engine:
            time_ms = self._synth_engine.current_time_ms
        if time_ms is None:
            return None
        
        # 二分查找: 找到 time_ms 对应的拍(使用预提取的排序列表)
        idx = bisect.bisect_right(self._timeline_times, time_ms) - 1
        
        if idx < 0:
            # 还没到第一个拍
            entry = self._playhead_timeline[0]
            return (
                entry['page_idx'], entry['sys_idx'], entry['meas_idx'],
                -1, entry['x_start'], 0.0
            )
        elif idx >= len(self._playhead_timeline) - 1:
            # 已超过最后一个拍
            entry = self._playhead_timeline[-1]
            return (
                entry['page_idx'], entry['sys_idx'], entry['meas_idx'],
                entry['beat_idx'], entry['x_end'], 1.0
            )
        else:
            # 在两个拍之间 → 插值计算精确X坐标
            curr = self._playhead_timeline[idx]
            next_e = self._playhead_timeline[idx + 1]
            
            dt = next_e['time_ms'] - curr['time_ms']
            progress = (time_ms - curr['time_ms']) / dt if dt > 0 else 0.0
            
            # X坐标线性插值
            x_pos = curr['x_center'] + progress * (next_e['x_center'] - curr['x_center'])
            
            return (
                curr['page_idx'], curr['sys_idx'], curr['meas_idx'],
                curr['beat_idx'], x_pos, progress
            )
    
    def time_to_scroll_pos(self, time_ms: float, 
                           total_scroll_distance: float,
                           display_height: int) -> float:
        """
        根据音频时间计算对应的滚动Y位置
        
        原理:
          在 playhead_timeline 中二分查找当前时间对应的拍，
          通过线性插值获取精确的 scroll_y 值。
          这使得滚动位置随音符时值自动变化：
          - 音符密集区(16/32分音符): 相同时间→更大scroll_y变化 → 滚动更快
          - 音符稀疏区(全/二分音符): 相同时间→更小scroll_y变化 → 滚动更慢
          
        参数:
            time_ms:             当前音频播放时间(毫秒)
            total_scroll_distance: 总滚动距离(像素)
            display_height:       显示区域高度(像素)，用于居中计算
            
        返回:
            对应的滚动Y位置(像素)，范围 [0, total_scroll_distance]
        """
        if not self._playhead_timeline or total_scroll_distance <= 0:
            return 0.0

        # 边界处理
        if time_ms <= 0:
            return 0.0
        if time_ms >= self._playhead_timeline[-1]['time_ms']:
            return float(total_scroll_distance)

        # 二分查找时间位置(使用预提取的排序列表)
        idx = bisect.bisect_right(self._timeline_times, time_ms) - 1

        if idx < 0:
            return 0.0
        if idx >= len(self._playhead_timeline) - 1:
            return float(total_scroll_distance)

        # 线性插值
        curr = self._playhead_timeline[idx]
        next_e = self._playhead_timeline[idx + 1]
        dt = next_e['time_ms'] - curr['time_ms']
        if dt <= 0:
            scroll_y = curr['scroll_y']
        else:
            t = (time_ms - curr['time_ms']) / dt
            scroll_y = curr['scroll_y'] + t * (next_e['scroll_y'] - curr['scroll_y'])

        # 映射到显示区域(减去可视区域高度的一半，让光标居中)
        centered_pos = max(0, scroll_y - display_height / 2)

        return min(centered_pos, float(total_scroll_distance))
    
    def scroll_pos_to_time(self, scroll_pos: float,
                           total_scroll_distance: float,
                           display_height: int) -> float:
        """
        根据滚动Y位置反推对应的音频时间 — time_to_scroll_pos 的逆运算
        
        原理:
          在 playhead_timeline 中对 scroll_y 做二分查找，
          通过线性插值获取精确的 time_ms 值。
          这是 time_to_scroll_pos() 的完全对称逆操作。
        
        为什么不能用线性比例?
          因为 scroll_y 与 time_ms 的关系是非线性的：
          - 密集区: 相同时间内scroll_y变化大 → 每像素对应少时间
          - 稀疏区: 相同时间内scroll_y变化小 → 每像素对应多时间
          用线性比例会在密集区高估时间(音频跳到后面)，导致"提前"感
          
        参数:
            scroll_pos:          滚动位置(像素)，已减去display_h/2的居中值
            total_scroll_distance: 总滚动距离(像素)
            display_height:      显示区域高度(像素)
            
        返回:
            对应的音频时间(毫秒)
        """
        if not self._playhead_timeline or total_scroll_distance <= 0:
            return 0.0
        
        # 边界处理
        if scroll_pos <= 0:
            return 0.0
        if scroll_pos >= total_scroll_distance:
            return self._total_audio_duration_ms
        
        # 将居中位置还原为原始scroll_y(与time_to_scroll_pos中的操作相反)
        raw_scroll_y = scroll_pos + display_height / 2
        
        # 对scroll_y做二分查找(使用预提取的排序列表，与time_to_scroll_pos对称)
        idx = bisect.bisect_right(self._timeline_scroll_ys, raw_scroll_y) - 1
        
        if idx < 0:
            return self._playhead_timeline[0]['time_ms']
        if idx >= len(self._playhead_timeline) - 1:
            return self._playhead_timeline[-1]['time_ms']
        
        # 线性插值(与time_to_scroll_pos对称)
        curr = self._playhead_timeline[idx]
        next_e = self._playhead_timeline[idx + 1]
        dy = next_e['scroll_y'] - curr['scroll_y']
        if dy <= 0:
            return curr['time_ms']
        
        t = (raw_scroll_y - curr['scroll_y']) / dy
        time_ms = curr['time_ms'] + t * (next_e['time_ms'] - curr['time_ms'])
        
        return max(0.0, time_ms)
    
    # ================================================================
    # 工具方法
    # ================================================================
    
    def create_error_image(self, message: str, width: int = 800, 
                           height: int = 500) -> QPixmap:
        """
        创建错误/信息展示图（当GTP引擎不可用时回退显示）
        
        参数:
            message: 显示的错误/信息文本
            width:   图片宽度(px)
            height:  图片高度(px)
            
        返回:
            包含错误信息的 QPixmap 图像
        """
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor('#252536'))  # 使用深色主题背景
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 标题
        painter.setPen(QColor('#3B82F6'))
        title_font = QFont("Microsoft YaHei", 26, QFont.Bold)
        painter.setFont(title_font)
        filename = "" if not self._file_path else self._file_path
        painter.drawText(QRect(50, 40, width - 100, 60), 
                        Qt.AlignCenter, f"Guitar Pro 文件: {filename}")

        # 信息文本
        painter.setPen(QColor('#E2E8F0'))
        info_font = QFont("Microsoft YaHei", 13)
        painter.setFont(info_font)
        
        lines = message.split('\n')
        y = 130
        for line in lines:
            if line.strip():
                painter.drawText(QRect(50, y, width - 100, 32), Qt.AlignLeft, line)
            y += 30

        # 边框
        painter.setPen(QPen(QColor('#3B82F6'), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(30, 30, width - 60, height - 60, 15, 15)
        painter.end()
        
        return pixmap
    
    def __del__(self):
        """析构时确保释放音频资源"""
        self.shutdown()


# ============================================================
# 便捷函数
# ============================================================

def create_gtp_player(gain: float = 0.7) -> GTPPlayer:
    """
    便捷工厂函数：创建并返回 GTPPlayer 实例
    
    参数:
        gain: 主音量(0.0-1.0), 调整效果: 0.7=适中音量
        
    返回:
        GTPPlayer 实例
        
    示例:
        >>> from gtp_engine.player import create_gtp_player
        >>> player = create_gtp_player(gain=0.8)
        >>> player.load("song.gp5")
        >>> images = player.render_track(0)
    """
    return GTPPlayer(gain=gain)


def render_gtp_to_images(file_path: str, track_index: int = 0,
                         config: RenderConfig = None) -> List[QPixmap]:
    """
    便捷函数：一键渲染GTP文件为图像列表
    
    参数:
        file_path:   .gp3/.gp4/.gp5/.gpx 文件路径
        track_index: 音轨索引（默认第1条）
        config:      自定义渲染配置（可选）
        
    返回:
        QPixmap列表，每元素对应一页乐谱图像
        
    示例:
        >>> from gtp_engine.player import render_gtp_to_images
        >>> pages = render_gtp_to_images("my_song.gp5", track_index=0)
        >>> pages[0].save("output.png", "PNG")
    """
    player = GTPPlayer()
    return player.render_track(track_index, config)
