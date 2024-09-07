import os
import sys
from collections import deque
from enum import Enum
from typing import Literal


class CellStat(Enum):
    E = "EMPTY"
    X = "X"
    O = "O"


class HypothesisStat(Enum):
    INDETERMINATE = "INDETERMINATE"
    DETERMINATE = "DETERMINATE"
    X = "X"
    O = "O"


class NonogramSolver:
    def __init__(
        self,
        row_hints: list[list[int]],
        column_hints: list[list[int]],
    ):
        self.n = len(row_hints)
        self.m = len(column_hints)
        self.board = [[CellStat.E for _ in range(self.m)] for _ in range(self.n)]
        self.r_hint = row_hints
        self.c_hint = column_hints
        self.r_solved = [False] * self.n
        self.c_solved = [False] * self.m
        self.r_inqueue = [True] * self.n
        self.c_inqueue = [True] * self.m
        self.task_queue: deque[tuple[Literal["row", "col"], int]] = deque(
            maxlen=self.n + self.m
        )

        initial_tasks: list[tuple[Literal["row", "col"], int]] = []
        for i in range(self.n):
            if not self.r_solved[i]:
                initial_tasks.append(("row", i))

        for j in range(self.m):
            if not self.c_solved[j]:
                initial_tasks.append(("col", j))

        initial_tasks = sorted(
            initial_tasks,
            key=lambda x: max(
                (hints if (hints := self.r_hint[x[1]]) else [self.n])
                if x[0] == "row"
                else (hints if (hints := self.c_hint[x[1]]) else [self.m])
            ),
            reverse=True,
        )
        self.task_queue.extend(initial_tasks)

    def solve(self):
        self.iteration = 1
        while not self.check_all_solved():
            if not self.task_queue:
                raise Exception("Faild to solve problem.")

            dir, num = self.task_queue.popleft()
            if dir == "row":
                self.r_inqueue[num] = False
                if self.r_solved[num]:
                    continue
                line = self.board[num].copy()
                hints = self.r_hint[num]
            elif dir == "col":
                self.c_inqueue[num] = False
                if self.c_solved[num]:
                    continue
                line = [r[num] for r in self.board]
                hints = self.c_hint[num]

            if not self.check_makable(line, hints):
                continue

            hypothesis_stats = self.test_hypothesis(line, hints)
            line_solved = True

            if dir == "row":
                for j, h_stat in enumerate(hypothesis_stats):
                    if h_stat == HypothesisStat.O or h_stat == HypothesisStat.X:
                        self.board[num][j] = CellStat[h_stat.value]
                        if not self.c_inqueue[j]:
                            self.task_queue.appendleft(("col", j))
                            self.c_inqueue[j] = True

                    if self.board[num][j] == CellStat.E:
                        line_solved = False
            elif dir == "col":
                for i, h_stat in enumerate(hypothesis_stats):
                    if h_stat == HypothesisStat.O or h_stat == HypothesisStat.X:
                        self.board[i][num] = CellStat[h_stat.value]
                        if not self.r_inqueue[i]:
                            self.task_queue.appendleft(("row", i))
                            self.r_inqueue[i] = True

                    if self.board[i][num] == CellStat.E:
                        line_solved = False

            if line_solved:
                if dir == "row":
                    self.r_solved[num] = True
                elif dir == "col":
                    self.c_solved[num] = True

            self.print_board()

    def test_hypothesis(self, line: list[CellStat], hints: list[int]):
        hypothesis_stats = [
            (
                HypothesisStat.INDETERMINATE
                if cs == CellStat.E
                else HypothesisStat.DETERMINATE
            )
            for cs in line
        ]

        self.recursive_test_hypothesis(line, hypothesis_stats, hints, 0, 0)

        return hypothesis_stats

    def recursive_test_hypothesis(
        self,
        line: list[CellStat],
        hypothesis_stats: list[HypothesisStat],
        hints: list[int],
        hint_idx: int,
        position_idx: int,
    ):
        if hint_idx == len(hints):
            if not hints:
                for i in range(len(hypothesis_stats)):
                    hypothesis_stats[i] = HypothesisStat.X
                return

            for i, cell_stat in enumerate(line):
                if cell_stat == CellStat.E:
                    line[i] = CellStat.X

            for i, (cell_stat, hypo_stat) in enumerate(zip(line, hypothesis_stats)):
                if hypo_stat == HypothesisStat.DETERMINATE:
                    continue

                if hypo_stat == HypothesisStat.INDETERMINATE:
                    if cell_stat == CellStat.O:
                        hypothesis_stats[i] = HypothesisStat.O
                    elif cell_stat == CellStat.X:
                        hypothesis_stats[i] = HypothesisStat.X
                    continue

                if (cell_stat == CellStat.O and hypo_stat == HypothesisStat.X) or (
                    cell_stat == CellStat.X and hypo_stat == HypothesisStat.O
                ):
                    hypothesis_stats[i] = HypothesisStat.DETERMINATE

            return

        block_len = hints[hint_idx]
        for i in range(position_idx, len(line)):
            if self.can_put(line, i, block_len, hints, hint_idx):
                new_hypothesis = line.copy()
                new_hypothesis[i : i + block_len] = [CellStat.O] * block_len
                self.recursive_test_hypothesis(
                    new_hypothesis,
                    hypothesis_stats,
                    hints,
                    hint_idx + 1,
                    i + block_len + 1,
                )

    def can_put(
        self,
        line: list[CellStat],
        idx: int,
        length: int,
        hints: list[int],
        hint_idx: int,
    ):
        if idx + length > len(line):
            return False

        if idx > 0 and line[idx - 1] == CellStat.O:
            return False

        if idx + length < len(line) and line[idx + length] == CellStat.O:
            return False

        for i in range(length):
            if line[idx + i] == CellStat.X:
                return False

        hypothesis = line.copy()
        hypothesis[idx : idx + length] = [CellStat.O] * length
        if not self.check_hypothesis_seq(hypothesis, hints, hint_idx):
            return False

        return True

    def check_makable(self, line: list[CellStat], hints: list[int]):
        if not hints:
            return True

        if any([c != CellStat.E for c in line]):
            return True

        largest_block = max(hints)
        empty_cells = sum([c == CellStat.E for c in line])
        doi = empty_cells - (sum(hints) + len(hints) - 1)

        return largest_block > doi

    def check_hypothesis_seq(
        self, hypothesis: list[CellStat], hints: list[int], hint_idx: int
    ):
        max_possible_blocks = len(hypothesis) // 2 + 1
        line_blocks = [0] * max_possible_blocks
        block_count = 0
        cnt = 0

        for cs in hypothesis:
            if cs == CellStat.O:
                cnt += 1
            elif cnt > 0:
                line_blocks[block_count] = cnt
                block_count += 1
                cnt = 0

        if cnt > 0:
            line_blocks[block_count] = cnt
            block_count += 1

        if line_blocks[: hint_idx + 1] != hints[: hint_idx + 1]:
            return False

        if sum(line_blocks[hint_idx + 1 : block_count]) > sum(hints[hint_idx + 1 :]):
            return False

        return True

    def check_all_solved(self):
        return all(self.r_solved) and all(self.c_solved)

    def print_board(self):
        board_txt = f"# {self.iteration}\n"
        for i in range(self.n):
            for j in range(self.m):
                cell_stat = self.board[i][j]

                if cell_stat == CellStat.E:
                    board_txt += "❔"
                elif cell_stat == CellStat.X:
                    board_txt += "⬜"
                elif cell_stat == CellStat.O:
                    board_txt += "⬛"
            board_txt += "\n"

        os.system("clear")
        sys.stdout.write(board_txt)

        self.iteration += 1

