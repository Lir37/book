#!/usr/bin/env python3
"""Canonical RPG regression tests for 26-chapter book and proposed levels 1..100."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'Книга про всякое, попытка 90123... (2).txt'
SPECS = ROOT / 'RPG_ЭЙДОС_СПЕЦИФИКАЦИЯ_v0.3_ИССЛЕДОВАНИЕ_2026-10-20.md'
LEVELS = ROOT / 'RPG_ЭЙДОС_ТАБЛИЦА_УРОВНЕЙ_1-100_2026-10-20.md'


def cost(level: int) -> int:
    if not 1 <= level < 100:
        raise ValueError('level must be between 1 and 99')
    if level < 3:
        return 300
    return 25 * int((600 + 75 * (level - 3) ** 1.5) / 25 + 0.5)


def total_for(level: int) -> int:
    if not 1 <= level <= 100:
        raise ValueError('level must be between 1 and 100')
    return sum(cost(current) for current in range(1, level))


class RPGRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.book = BOOK.read_text(encoding='utf-8')
        cls.spec = SPECS.read_text(encoding='utf-8')
        cls.levels = LEVELS.read_text(encoding='utf-8')
        cls.chapters = re.split(r'(?m)^(?=Глава \d+(?:\.|\n))', cls.book)
        cls.chapters = [c for c in cls.chapters if re.match(r'^Глава \d+', c)]

    def test_early_cumulative_xp(self):
        self.assertEqual([total_for(k) for k in (1, 2, 3, 4, 5, 6)],
                         [0, 300, 600, 1200, 1875, 2675])

    def test_100_level_curve(self):
        self.assertEqual(total_for(100), 2803300)
        self.assertEqual(cost(99), 71150)
        self.assertTrue(all(cost(n + 1) >= cost(n) for n in range(3, 99)))
        self.assertTrue(all(cost(n) % 25 == 0 for n in range(3, 100)))
        self.assertIn('2 803 300', self.levels)

    def test_book_length_and_chapters(self):
        self.assertEqual(len(self.chapters), 26)
        self.assertGreaterEqual(len(self.book), 350000)
        self.assertIn('Осквернённые корни', self.chapters[11][:120])
        self.assertIn('Сердце под корнями', self.chapters[12][:120])

    def test_no_old_hp_or_stats(self):
        self.assertFalse(re.search(r'Здоровье:\s*\d+|(?:Интеллект|Удача)\s*[—:]', self.book))
        self.assertIn('Живучесть — 10.', self.book)
        self.assertIn('Восприятие — 13.', self.book)

    def test_earned_stat_points(self):
        self.assertIn('ловкость 14, дух 16', self.chapters[4])
        self.assertIn('выносливость 11, живучесть 11, дух 17', self.chapters[7])
        self.assertEqual(sum([8, 12, 10, 10, 13, 15]), 68)
        self.assertEqual(sum([8, 14, 10, 10, 13, 16]), 71)
        self.assertEqual(sum([8, 14, 11, 11, 13, 17]), 74)

    def test_form_costs_and_mastery(self):
        self.assertIn('5 единиц в секунду', self.chapters[4])
        self.assertIn('1,00 → 1,05', self.chapters[4])
        self.assertIn('на переключение форм снижен на 30%', self.chapters[5])
        self.assertIn('Мягкая смена', self.chapters[15])
        self.assertIn('Урсалон и Скайрэйвен снова стали серыми значками', self.chapters[5])

    def test_xp_in_book_not_recalculated(self):
        for token in ('150 / 300', '300/600', '450/600', '550/600',
                      '825/1200', '925/1200', '975/1200', '1075/1200'):
            self.assertIn(token, self.book)
        self.assertNotIn('2 803 300', self.book)  # full curve stays behind the scenes

    def test_death_stays_final(self):
        self.assertIn('сообщение о возрождении', self.chapters[24])
        self.assertIn('после смерти', self.chapters[25])
        self.assertIn('целыми', self.chapters[24] + self.chapters[25])

    def test_research_project_separation(self):
        self.assertIn('ПРОЕКТ', self.spec)
        self.assertIn('125 маны', self.spec)
        self.assertIn('5 маны/сек', self.spec)

if __name__ == '__main__':
    unittest.main(verbosity=2)
