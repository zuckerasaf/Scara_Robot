from pathlib import Path


# Markers 15-23 are the physical Tic Tac Toe cell centers.
DEFAULT_CELL_MARKER_IDS = [
    [1, 4, 7],
    [12, 15, 18],
    [14, 17, 20],
]


def load_cell_marker_ids(config_path=None):
    """Load the 3x3 cell-to-marker map from board_configuration.txt."""
    if config_path is None:
        config_path = Path(__file__).resolve().parents[1] / "board_configuration.txt"

    try:
        lines = Path(config_path).read_text().splitlines()
    except OSError:
        return [row[:] for row in DEFAULT_CELL_MARKER_IDS]

    marker_rows = []
    for line in lines:
        if "marker" not in line.lower():
            continue

        marker_ids = []
        for part in line.replace("\t", " ").split("|"):
            tokens = part.strip().split()
            if len(tokens) >= 2 and tokens[0].lower() == "marker":
                try:
                    marker_ids.append(int(tokens[1]))
                except ValueError:
                    pass

        if len(marker_ids) == 3:
            marker_rows.append(marker_ids)

    if len(marker_rows) == 3:
        return marker_rows

    return [row[:] for row in DEFAULT_CELL_MARKER_IDS]


CELL_MARKER_IDS = load_cell_marker_ids()


# Shared 3x3 game state; each cell keeps a stable id, symbol, marker, and live location.
board = [
    [
        {"id": 0, "status": " ", "marker_id": CELL_MARKER_IDS[0][0], "location": None},
        {"id": 1, "status": " ", "marker_id": CELL_MARKER_IDS[0][1], "location": None},
        {"id": 2, "status": " ", "marker_id": CELL_MARKER_IDS[0][2], "location": None},
    ],
    [
        {"id": 3, "status": " ", "marker_id": CELL_MARKER_IDS[1][0], "location": None},
        {"id": 4, "status": " ", "marker_id": CELL_MARKER_IDS[1][1], "location": None},
        {"id": 5, "status": " ", "marker_id": CELL_MARKER_IDS[1][2], "location": None},
    ],
    [
        {"id": 6, "status": " ", "marker_id": CELL_MARKER_IDS[2][0], "location": None},
        {"id": 7, "status": " ", "marker_id": CELL_MARKER_IDS[2][1], "location": None},
        {"id": 8, "status": " ", "marker_id": CELL_MARKER_IDS[2][2], "location": None},
    ],
]

Empty = " "
# All index triplets that represent a winning line on a 3x3 board.
WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


def get_cell_by_id(cell_id):
    for row in board:
        for cell in row:
            if cell["id"] == cell_id:
                return cell
    return None


def get_cell_location(cell_id):
    """Return the current robot-coordinate location for a Tic Tac Toe cell."""
    cell = get_cell_by_id(cell_id)
    if cell is None:
        return None
    return cell.get("location")


def get_cell_marker_map():
    """Return {cell_id: marker_id} for the physical board layout."""
    return {cell["id"]: cell["marker_id"] for row in board for cell in row}


def update_cell_locations(marker_positions):
    """Update cell locations from a marker_id -> (x, y) mapping."""
    updated = 0

    for row in board:
        for cell in row:
            marker_id = cell["marker_id"]
            if marker_id not in marker_positions:
                cell["location"] = None
                continue

            x_val, y_val = marker_positions[marker_id]
            cell["location"] = {"x": float(x_val), "y": float(y_val)}
            updated += 1

    return updated


def get_current_marker_positions(calibration, marker_ids=None, use_config_fallback=False):
    """Read current detected marker centers and convert them to robot coordinates."""
    if marker_ids is None:
        marker_ids = sorted(set(get_cell_marker_map().values()))

    positions = {}

    for marker_id in marker_ids:
        data = calibration.confirmed_markers.get(marker_id)
        if data and data.get("corners") and calibration.is_calibrated:
            latest_corners = data["corners"][-1]
            center_x = sum(float(point[0]) for point in latest_corners) / len(latest_corners)
            center_y = sum(float(point[1]) for point in latest_corners) / len(latest_corners)

            robot_pos = calibration.camera_to_robot(center_x, center_y)
            if robot_pos is not None:
                positions[marker_id] = (float(robot_pos[0]), float(robot_pos[1]))
                continue

        if use_config_fallback and marker_id in calibration.known_marker_positions:
            marker_pos = calibration.known_marker_positions[marker_id]
            positions[marker_id] = (float(marker_pos["x"]), float(marker_pos["y"]))

    return positions


def update_cell_locations_from_calibration(calibration, use_config_fallback=False):
    """Use current detected marker positions as the physical Tic Tac Toe cell locations."""
    marker_positions = get_current_marker_positions(
        calibration,
        use_config_fallback=use_config_fallback,
    )
    return update_cell_locations(marker_positions)


def print_ids():
    # Show the fixed ids users can type as commands.
    print("\nBoard IDs:")
    for row in board:
        print(
            f" {row[0]['id']}[M{row[0]['marker_id']}] | "
            f"{row[1]['id']}[M{row[1]['marker_id']}] | "
            f"{row[2]['id']}[M{row[2]['marker_id']}] "
        )
        if row != board[-1]:
            print("---------+---------+---------")


def print_board():
    # Render the current board symbols after each valid move.
    print("\nCurrent Board:")
    for row in board:
        print(
            f" {row[0]['status']} | {row[1]['status']} | {row[2]['status']} "
        )
        if row != board[-1]:
            print("---+---+---")


def set_move(cell_id, player):
    # Write a move only if the selected cell exists and is empty.
    cell = get_cell_by_id(cell_id)

    if cell is None:
        print("Invalid ID")
        return False

    if cell["status"] != " ":
        print("Cell already occupied")
        return False

    cell["status"] = player
    return True


def check_winner(player):
    # Build every winning line (rows, columns, diagonals) and test for 3-in-a-row.
    lines = []

    # Rows
    for row in board:
        lines.append([row[0]["status"], row[1]["status"], row[2]["status"]])

    # Columns
    for col in range(3):
        lines.append([board[0][col]["status"], board[1][col]["status"], board[2][col]["status"]])

    # Diagonals
    lines.append([board[0][0]["status"], board[1][1]["status"], board[2][2]["status"]])
    lines.append([board[0][2]["status"], board[1][1]["status"], board[2][0]["status"]])

    return [player, player, player] in lines


def get_board_state():
    # Flatten the board into a 9-cell list for minimax evaluation.
    state = [Empty] * 9
    for row in board:
        for cell in row:
            state[cell["id"]] = cell["status"]
    return state


def check_winner_in_state(state, player):
    # Fast winner check against the flattened board state.
    for i, j, k in WIN_LINES:
        if state[i] == player and state[j] == player and state[k] == player:
            return True
    return False


def is_state_full(state):
    # State is full when no empty slots remain.
    return Empty not in state


def minimax(state, is_maximizing, ai_symbol, human_symbol):
    # Score terminal states from the AI perspective.
    if check_winner_in_state(state, ai_symbol):
        return 1
    if check_winner_in_state(state, human_symbol):
        return -1
    if is_state_full(state):
        return 0

    if is_maximizing:
        best_score = -100
        for move in range(9):
            if state[move] == Empty:
                state[move] = ai_symbol
                score = minimax(state, False, ai_symbol, human_symbol)
                state[move] = Empty
                if score > best_score:
                    best_score = score
        return best_score

    best_score = 100
    for move in range(9):
        if state[move] == Empty:
            state[move] = human_symbol
            score = minimax(state, True, ai_symbol, human_symbol)
            state[move] = Empty
            if score < best_score:
                best_score = score
    return best_score


class Player:
    def __init__(self, name, symbol):
        self.name = name
        self.symbol = symbol
        self.winning_status = False

    def update_winning_status(self):
        # Keep the player's win flag aligned with the current board.
        self.winning_status = check_winner(self.symbol)
        return self.winning_status

    def command(self, cell_id):
        # Player command = attempt move, then refresh win state if move succeeded.
        move_set = set_move(cell_id, self.symbol)
        if move_set:
            self.update_winning_status()
        return move_set


class ComputerPlayer(Player):
    def __init__(self, name, symbol, human_symbol):
        super().__init__(name, symbol)
        self.human_symbol = human_symbol

    def choose_best_move(self):
        # Try every legal move and keep the move with the highest minimax score.
        state = get_board_state()
        best_score = -100
        best_move = None

        for move in range(9):
            if state[move] == Empty:
                state[move] = self.symbol
                score = minimax(state, False, self.symbol, self.human_symbol)
                state[move] = Empty
                if score > best_score:
                    best_score = score
                    best_move = move

        return best_move

    def command(self):
        # Computer turn: pick the best move, play it, then refresh win state.
        best_move = self.choose_best_move()
        if best_move is None:
            return False

        location = get_cell_location(best_move)
        if location:
            print(
                f"\n{self.name} ({self.symbol}) chooses cell {best_move} "
                f"at ({location['x']:.2f}, {location['y']:.2f})"
            )
        else:
            print(f"\n{self.name} ({self.symbol}) chooses cell {best_move}")

        move_set = set_move(best_move, self.symbol)
        if move_set:
            self.update_winning_status()
        return move_set


def is_board_full():
    # Draw condition: no remaining empty cells.
    for row in board:
        for cell in row:
            if cell["status"] == " ":
                return False
    return True


def run_game():
    # Main loop: human enters a move, computer calculates a move, then game state is checked.
    player_x = Player("Player X", "X")
    player_o = ComputerPlayer("Computer", "O", "X")
    current_player = player_x

    print("Tic Tac Toe Started")
    print_ids()
    print_board()

    while True:
        if isinstance(current_player, ComputerPlayer):
            move_done = current_player.command()
        else:
            try:
                raw_command = input(
                    f"\n{current_player.name} ({current_player.symbol}) choose cell id (0-8): "
                ).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGame cancelled by user")
                break

            if not raw_command.isdigit():
                print("Please enter a valid number from 0 to 8")
                continue

            cell_id = int(raw_command)
            move_done = current_player.command(cell_id)

        if not move_done:
            continue

        print_board()

        if current_player.winning_status:
            print(f"\n{current_player.name} wins")
            break

        if is_board_full():
            print("\nGame ended in a draw")
            break

        current_player = player_o if current_player == player_x else player_x


if __name__ == "__main__":
    run_game()
