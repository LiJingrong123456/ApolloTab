# -*- coding: utf-8 -*-
"""
============================================================
ApolloTab - Guitar Pro 文件渲染与播放引擎库
============================================================

功能概述:
  本库提供 Guitar Pro (.gp3/.gp4/.gp5/.gpx) 文件的完整解析、渲染与播放能力，
  可作为独立库发布到 PyPI，也可集成到 TAB Score Viewer 主程序中。

核心模块:
  - parser:    GTP文件解析 (PyGuitarPro → 中介数据模型)
  - models:    数据模型定义 (Note/Beat/Measure/Track/Song)
  - renderer:  六线谱渲染引擎 (QPainter → QPixmap)
  - audio:     音频播放引擎 (MIDI转换 + FluidSynth合成)
  - player:    高级播放器封装 (整合解析/渲染/音频/时间线的完整流程)
  - utils:     常量定义与辅助函数

快速开始:
    # 方式1: 使用高级API（推荐，最简单）
    from ApolloTab import GTPPlayer
    
    player = GTPPlayer()
    player.load("my_song.gp5")
    images = player.render_track(0)       # 渲染六线谱
    player.init_audio()                   # 初始化音频（可选）
    player.play()                         # 开始播放
    
    # 方式2: 分步操作（更灵活）
    from ApolloTab import parse_gtp, TabRenderer, SynthEngine, MidiConverter
    
    song = parse_gtp("my_song.gp5")
    print(f"标题: {song.title}, 音轨: {song.track_count}")
    
    # 方式3: 一键渲染
    from ApolloTab import render_gtp
    pages = render_gtp("my_song.gp5", track_index=0)
    
依赖库:
  - guitarpro >= 0.11   # Guitar Pro 文件解析（开源项目: pyguitarpro）
  - PyQt5 >= 5.15       # GUI渲染（用于生成QPixmap图像）
  - pyfluidsynth >= 1.4.0  # 音频合成（可选，仅音频播放时需要）

版本: v0.2.0 (Phase 4 - 库化重构 + 高级播放器API)
许可证: Mozilla Public License 2.0 (MPL-2.0)
创建日期: 2026-06-06
最后更新: 2026-06-12
============================================================
"""

from .parser import GTPParser, parse_gtp
from .models import GTPNote, GTPBeat, GTPMeasure, GTPTrack, GTPSong
from .renderer import TabRenderer, render_gtp, TabLayoutEngine
from .audio import MidiConverter, MidiEvent, SynthEngine
from .player import GTPPlayer, create_gtp_player, render_gtp_to_images
from .utils import (
    StandardTunings, NoteDuration, TechniqueType,
    RenderConfig, TECHNIQUE_ABBREVIATION, get_string_name
)

__version__ = "0.2.0"
__all__ = [
    # ===== 高级API（推荐）=====
    'GTPPlayer',              # 高级播放器封装类（整合所有GTP功能）
    'create_gtp_player',      # 工厂函数：快速创建播放器实例
    'render_gtp_to_images',   # 便捷函数：一键渲染为图像列表
    
    # 解析器
    'GTPParser', 'parse_gtp',
    # 数据模型
    'GTPNote', 'GTPBeat', 'GTPMeasure', 'GTPTrack', 'GTPSong',
    # 渲染器
    'TabRenderer', 'render_gtp', 'TabLayoutEngine',
    # 音频播放
    'MidiConverter', 'MidiEvent', 'SynthEngine',
    # 工具
    'StandardTunings', 'NoteDuration', 'TechniqueType',
    'RenderConfig', 'TECHNIQUE_ABBREVIATION', 'get_string_name',
]
