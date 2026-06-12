# -*- coding: utf-8 -*-
"""
============================================================
文件名: beat.py
功能描述: 拍(Beat)数据模型 - 存储一拍内同时发声的所有音符
         一拍可以包含多个音符(和弦)或一个休止符

创建日期: 2026-06-06
依赖: Python 3.8+ dataclasses
============================================================
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .note import GTPNote
from ..utils.constants import NoteDuration


@dataclass
class GTPBeat:
    """
    一拍(Beat)的数据模型 - 对应 Guitar Pro 中 Voice 内的一个 Beat
    
    属性说明:
      notes:     该拍内的所有音符列表（同时发声构成和弦）
      duration:  时值类型 (四分/八分/十六分等)
      is_dotted: 是否附点
      text:      该拍上的文字标注（如演奏提示）
      is_rest:   是否为休止符拍
    """

    notes: List[GTPNote] = field(default_factory=list)  # 音符列表（同时发声）
    duration: NoteDuration = NoteDuration.QUARTER        # 时值
    is_dotted: bool = False                              # 是否附点
    text: Optional[str] = None                           # 文字标注
    is_rest: bool = False                                # 是否休止符

    @property
    def is_empty(self) -> bool:
        """判断该拍是否为空（无音符且非休止符）"""
        return len(self.notes) == 0 and not self.is_rest

    @property
    def duration_value(self) -> float:
        """
        获取以四分音符为基准的实际时长
        返回: 浮点数时长，如四分音符=1.0, 附点八分音符=0.75
        """
        from ..utils.constants import DURATION_RATIO, DOTTED_MULTIPLIER
        base = DURATION_RATIO.get(self.duration.value, 1.0)
        if self.is_dotted:
            base *= DOTTED_MULTIPLIER
        return base

    def get_highest_string(self) -> int:
        """获取该拍中最高(最细)弦的索引，无音符返回-1"""
        if not self.notes:
            return -1
        return min(n.string for n in self.notes)

    def get_lowest_string(self) -> int:
        """获取该拍中最低(最粗)弦的索引，无音符返回-1"""
        if not self.notes:
            return -1
        return max(n.string for n in self.notes)
