# -*- coding: utf-8 -*-
"""
gtp_engine.renderer - 渲染器模块
导出: TabRenderer 类、render_gtp 便捷函数、布局引擎类
"""
from .tab_renderer import TabRenderer, render_gtp
from .layout_engine import TabLayoutEngine, PageLayout, SystemLayout, MeasureLayout, BeatLayout
# RenderMode 从 utils.constants 导入(v0.4.0新增: 渲染模式枚举)
from ..utils.constants import RenderMode

__all__ = [
    'TabRenderer', 'render_gtp',
    'TabLayoutEngine', 'PageLayout', 'SystemLayout', 'MeasureLayout', 'BeatLayout',
    'RenderMode',  # v0.4.0新增: 渲染模式枚举
]
