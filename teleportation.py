import pygame
import sys
import random
import math

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import Initialize


from ibm_qc_interface import ideal_simulator, noisy_simulator


def bloch_to_statevector(bloch_vec):
    # Convert [x, z] Bloch vector to a quantum state vector, assuming y=0
    x, z = bloch_vec
    y = 0
    theta = np.arccos(z)         # polar angle
    phi = np.arctan2(y, x)       # azimuthal angle
    state = [np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)]
    return state

def build_teleportation_circuit_with_state(bloch_vec):
    qr = QuantumRegister(3)  # Qubits: Alice(0), Bell pair (1, 2)
    cr = ClassicalRegister(2)  # Two classical bits for measurement
    qc = QuantumCircuit(qr, cr)

    # Initialize Alice's qubit to the state from bloch_vec
    state = bloch_to_statevector(bloch_vec)
    init_gate = Initialize(state)
    qc.append(init_gate, [qr[0]])
    qc.barrier()

    # Prepare Bell pair between qubit 1 and 2
    qc.h(qr[1])
    qc.cx(qr[1], qr[2])

    # Teleportation steps
    qc.cx(qr[0], qr[1])
    qc.h(qr[0])

    # Measure Alice's qubits
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])

    return qc

# Pygame setup
pygame.init()
WIDTH, HEIGHT = 800, 420
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Teleportation Quest – Quantum Puzzle")
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)
tiny_font = pygame.font.SysFont(None, 18)

# New flag for measurement collapse
measured = False

WHITE = (255, 255, 255)
BLACK = (21, 2, 79)
RED = (199, 70, 175)
GREEN = (0, 153, 76)
BLUE = (70, 130, 230)
YELLOW = (70, 171, 199) # light blue
GRAY = (180, 180, 180)

clock = pygame.time.Clock()

sound_click = None
sound_measure = None
sound_success = None
sound_fail = None

PHASES = ["intro", "entangle", "measure", "measured", "bit_explanation", "send_bits", "bits_fly", "explain_gates", "result"]
phase = "intro"

alice_pos = (150, HEIGHT // 2 + 100)
bob_pos = (650, HEIGHT // 2 + 100)

entangled = False
measurement_result = ""
correction_chosen = ""
teleport_success = False
result_msg = ""
bit_message_shown = False
user_selected_bits = ""

bits_animating = False
bits_pos = list(alice_pos)
bits_target = bob_pos
bits_speed = 6

show_tooltip = False
tooltip_text = ""
tooltip_rect = pygame.Rect(0, 0, 0, 0)

bit_to_correction = {
    "00": "I",
    "01": "X",
    "10": "Z",
    "11": "XZ"
}

alice_bloch = [0, 1]
bob_bloch = [0, -1]

valid_bit_combos = {
    "01": [
        ([0, 1], [0, -1]), ([0, -1], [0, 1]),
        ([1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)]),
        ([-1/math.sqrt(2), 1/math.sqrt(2)], [-1/math.sqrt(2), -1/math.sqrt(2)]),
        ([1/math.sqrt(2), -1/math.sqrt(2)], [1/math.sqrt(2), 1/math.sqrt(2)]),
        ([-1/math.sqrt(2), -1/math.sqrt(2)], [-1/math.sqrt(2), 1/math.sqrt(2)])
    ],
    "10": [
        ([-1, 0], [1, 0]), ([1, 0], [-1, 0]),
        ([1/math.sqrt(2), 1/math.sqrt(2)], [-1/math.sqrt(2), 1/math.sqrt(2)]),
        ([-1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), 1/math.sqrt(2)]),
        ([1/math.sqrt(2), -1/math.sqrt(2)], [-1/math.sqrt(2), -1/math.sqrt(2)]),
        ([-1/math.sqrt(2), -1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)])
    ],
    "11": [
        ([1/math.sqrt(2), 1/math.sqrt(2)], [-1/math.sqrt(2), -1/math.sqrt(2)]),
        ([-1/math.sqrt(2), 1/math.sqrt(2)], [1/math.sqrt(2), -1/math.sqrt(2)]),
        ([1/math.sqrt(2), -1/math.sqrt(2)], [-1/math.sqrt(2), 1/math.sqrt(2)]),
        ([-1/math.sqrt(2), -1/math.sqrt(2)], [1/math.sqrt(2), 1/math.sqrt(2)])
    ]
}


def reset_game():
    global phase, entangled, measurement_result, correction_chosen, teleport_success, result_msg, bit_message_shown, bits_animating, bits_pos
    global alice_bloch, bob_bloch, user_selected_bits

    phase = "intro"
    entangled = False
    measured = False
    valid_pair_found = False
    while not valid_pair_found:
        alice_bloch = random.choice([
            [0, 1], [0, -1], [1, 0], [-1, 0],
            [1/math.sqrt(2), 1/math.sqrt(2)], [-1/math.sqrt(2), 1/math.sqrt(2)],
            [1/math.sqrt(2), -1/math.sqrt(2)], [-1/math.sqrt(2), -1/math.sqrt(2)]
        ])
        bob_bloch = random.choice([
            alice_bloch, [-alice_bloch[0], -alice_bloch[1]],
            [alice_bloch[1], -alice_bloch[0]], [-alice_bloch[1], alice_bloch[0]]
        ])

        if are_valid_bloch_vectors(alice_bloch, bob_bloch):
            valid_pair_found = True

    measurement_result = ""
    correction_chosen = ""
    teleport_success = False
    result_msg = ""
    bit_message_shown = False
    user_selected_bits = ""
    bits_animating = False
    bits_pos = list(alice_pos)

def is_valid_bit_selection(bits):
    if bits == "00":
        return True
    for a_vec, b_vec in valid_bit_combos.get(bits, []):
        if (math.isclose(a_vec[0], alice_bloch[0], abs_tol=0.4) and
            math.isclose(a_vec[1], alice_bloch[1], abs_tol=0.4) and
            math.isclose(b_vec[0], bob_bloch[0], abs_tol=0.4) and
            math.isclose(b_vec[1], bob_bloch[1], abs_tol=0.4)):
            return True
    return False

def are_valid_bloch_vectors(alice_vec, bob_vec):
    # Check if Alice and Bob are equal vectors (valid for "00")
    if math.isclose(alice_vec[0], bob_vec[0], abs_tol=0.1) and math.isclose(alice_vec[1], bob_vec[1], abs_tol=0.1):
        return True

    # Check if the pair exists in any valid_bit_combos list
    for bits, pairs in valid_bit_combos.items():
        for a_vec, b_vec in pairs:
            if (math.isclose(a_vec[0], alice_vec[0], abs_tol=0.4) and
                math.isclose(a_vec[1], alice_vec[1], abs_tol=0.4) and
                math.isclose(b_vec[0], bob_vec[0], abs_tol=0.4) and
                math.isclose(b_vec[1], bob_vec[1], abs_tol=0.4)):
                return True
    return False


def render_centered(text, y, color=BLACK):
    txt = font.render(text, True, color)
    rect = txt.get_rect(center=(WIDTH // 2, y))
    screen.blit(txt, rect)

def draw_bloch_sphere(pos, label, bloch_vector, collapsed=False):
    # Draw sphere outline
    pygame.draw.circle(screen, BLUE, pos, 50, 3)

    # Draw axes
    axis_len = 40
    pygame.draw.line(screen, RED, (pos[0] - axis_len, pos[1]), (pos[0] + axis_len, pos[1]), 2)
    pygame.draw.line(screen, GREEN, (pos[0], pos[1] - axis_len), (pos[0], pos[1] + axis_len), 2)
    diag_offset = int(axis_len / math.sqrt(2))
    pygame.draw.line(screen, YELLOW, (pos[0] - diag_offset, pos[1] - diag_offset),
                     (pos[0] + diag_offset, pos[1] + diag_offset), 2)

    vec_scale = 40
    end_x = pos[0] + int(bloch_vector[0] * vec_scale)
    end_y = pos[1] - int(bloch_vector[1] * vec_scale)  # invert y-axis

    if collapsed:
        color = RED
        width = 4
    else:
        color = BLACK
        width = 4

    pygame.draw.line(screen, color, pos, (end_x, end_y), width)

    # Arrowhead
    arrow_size = 10
    angle = math.atan2(pos[1] - end_y, end_x - pos[0])
    left = (end_x - arrow_size * math.cos(angle + math.pi / 6),
            end_y + arrow_size * math.sin(angle + math.pi / 6))
    right = (end_x - arrow_size * math.cos(angle - math.pi / 6),
             end_y + arrow_size * math.sin(angle - math.pi / 6))
    pygame.draw.polygon(screen, color, [(end_x, end_y), left, right])

    # Label
    txt = font.render(label, True, BLACK)
    screen.blit(txt, (pos[0] - txt.get_width() // 2, pos[1] + 60))


def draw_buttons(options, y):
    buttons = []
    spacing = 88
    start_x = 222
    for i, option in enumerate(options):
        rect = pygame.Rect(start_x + i * spacing, y, 80, 40)
        pygame.draw.rect(screen, BLUE, rect)
        txt = font.render(option, True, WHITE)
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)
        buttons.append((rect, option))
    return buttons


def draw_bit_selection_buttons():
    return draw_buttons(["00", "01", "10", "11"], 230)

# Main loop

def main():

    global running, phase, entangled, measured, measurement_result, correction_chosen
    global teleport_success, result_msg, bit_message_shown, user_selected_bits
    global bits_animating, bits_pos, bit_buttons, correction_buttons, show_tooltip


    running = True
    bit_buttons = []
    correction_buttons = []

    while running:
        screen.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if show_tooltip:
                    show_tooltip = False
                else:
                    if phase == "intro":
                        phase = "entangle"

                    elif phase == "entangle":
                        entangled = True
                        phase = "measure"
                
                    elif phase == "measure":
                        qc = build_teleportation_circuit_with_state(alice_bloch)
                        counts, shots = ideal_simulator(qc) # or noisy
                        measurement_result = max(counts, key=counts.get)
                        measurement_result = measurement_result[::-1]

                        print(f"Measurement result: {measurement_result}")  # Debug print to see bits

                        measured = True
                        phase = "measured"

                    elif phase == "measured":
                        phase = "bit_explanation"

                    elif phase == "bit_explanation":
                        phase = "send_bits"

                    elif phase == "send_bits":
                        pass  # wait for manual bit selection

                    elif phase == "bits_fly":
                        pass

                    elif phase == "explain_gates":
                    #     phase = "apply_correction"

                    # elif phase == "apply_correction":
                        for rect, opt in correction_buttons:
                            if rect.collidepoint(event.pos):
                                correction_chosen = opt
                                if correction_chosen == bit_to_correction[measurement_result]:
                                    teleport_success = True
                                    result_msg = "Teleportation successful! Bob got |ψ>."
                                else:
                                    teleport_success = False
                                    result_msg = f"Teleportation failed. You applied {correction_chosen}, but needed {bit_to_correction[measurement_result]}."
                                phase = "result"

                    elif phase == "result":
                        reset_game()

                # Bit selection
                if phase == "send_bits":
                    for rect, bits in bit_buttons:
                        if rect.collidepoint(event.pos):
                            if is_valid_bit_selection(bits):
                                user_selected_bits = bits
                                measurement_result = bits
                                bit_message_shown = True
                                bits_animating = True
                                bits_pos = list(alice_pos)
                                phase = "bits_fly"
                            else:
                                result_msg = f"Incorrect bits ({bits}) for current Bloch vectors!"
                                teleport_success = False
                                phase = "result"

        # PHASE DISPLAY

        if phase == "intro":
            render_centered("Welcome to Quantum Teleportation Quest", 100, YELLOW)
            render_centered("Click anywhere to begin your mission.", 160, RED)
            render_centered("Learn how quantum teleportation moves a quantum state", 220, BLACK)
            render_centered("from Alice's qubit to Bob's, using entanglement", 260, BLACK)
            render_centered("and classical communication.", 300, BLACK)

        elif phase == "entangle":
            render_centered("Entangle Alice's and Bob's qubits.", 60, YELLOW)
            render_centered("Entanglement is crucial for Quantum Teleportation.", 100, BLACK)
            render_centered("without it, the exchange between the 2 Qubits", 140, BLACK)
            render_centered("(no matter where they are) would not be possible.", 180, BLACK)
            draw_bloch_sphere(alice_pos, "Alice (Quantum State)", alice_bloch)
            draw_bloch_sphere(bob_pos, "Bob (Quantum State)", bob_bloch)
            render_centered("Click anywhere to entangle.", 220, RED)

        elif phase == "measure":
            render_centered("Alice measures her qubit.", 80, BLACK)
            draw_bloch_sphere(alice_pos, "Alice", alice_bloch)
            draw_bloch_sphere(bob_pos, "Bob", bob_bloch)
            if entangled:
                pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)
            render_centered("Click to perform measurement.", 180, RED)

        elif phase == "measured":
            render_centered("Alice's qubit has been measured.", 80, YELLOW)
            render_centered("The quantum state collapses to a definite value.", 120, BLACK)
            render_centered("Now Alice has classical bits to send to Bob.", 160, BLACK)

            draw_bloch_sphere(alice_pos, "Alice", alice_bloch, collapsed=True)
            draw_bloch_sphere(bob_pos, "Bob", bob_bloch)
            if entangled:
                pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)

            render_centered("The following Bits are available:", 200, RED)
            draw_buttons(["00", "01", "10", "11"], 230)

            

        elif phase == "bit_explanation":
            render_centered("How does classical information help?", 60, BLACK)
            render_centered("For Bob to recover Alice's original quantum state,", 100, BLACK)
            render_centered("he needs to know which quantum gate to apply to his qubit.", 130, BLACK)
            render_centered("To do that, Alice sends him two classical bits.", 160, BLACK)
            render_centered("These bits correlate with quantum gates Bob can apply:", 190, BLACK)

            render_centered("00 -> Identity (I) — No correction needed", 230, YELLOW)
            render_centered("01 -> X gate — Bit-flip (0 <-> 1)", 260, YELLOW)
            render_centered("10 -> Z gate — Phase-flip (+ <-> -)", 290, YELLOW)
            render_centered("11 -> XZ — Bit and Phase flip", 320, YELLOW)

            render_centered("Click anywhere to continue.", 360, RED)


        elif phase == "send_bits":
            render_centered("Alice sends classical bits to Bob.", 80, BLACK)
            draw_bloch_sphere(alice_pos, "Alice", alice_bloch, collapsed=True)
            draw_bloch_sphere(bob_pos, "Bob", bob_bloch)
            if entangled:
                pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)
            render_centered("Choose the correct bits to send:", 120, RED)
            bit_buttons = draw_buttons(["00", "01", "10", "11"], 160)

        elif phase == "bits_fly":
            draw_bloch_sphere(alice_pos, "Alice", alice_bloch, collapsed=True)
            draw_bloch_sphere(bob_pos, "Bob", bob_bloch)
            if entangled:
                pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)

            txt = font.render(f"Bits sent: {measurement_result}", True, BLACK)
            screen.blit(txt, (alice_pos[0] - txt.get_width() // 2, alice_pos[1] - 80))

            if bits_animating:
                bits_pos[0] += (bits_target[0] - bits_pos[0]) / bits_speed
                bits_pos[1] += (bits_target[1] - bits_pos[1]) / bits_speed

                pygame.draw.circle(screen, BLACK, (int(bits_pos[0]), int(bits_pos[1])), 12)
                bits_txt = small_font.render(measurement_result, True, WHITE)
                bits_txt_rect = bits_txt.get_rect(center=(int(bits_pos[0]), int(bits_pos[1])))
                screen.blit(bits_txt, bits_txt_rect)

                dist = math.hypot(bits_target[0] - bits_pos[0], bits_target[1] - bits_pos[1])
                if dist < 6:
                    bits_animating = False
                    phase = "explain_gates"

        elif phase == "explain_gates":
            draw_bloch_sphere(alice_pos, "Alice", alice_bloch, collapsed=True)
            draw_bloch_sphere(bob_pos, "Bob", bob_bloch)
            if entangled:
                pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)

            render_centered(f"Alice sent bits {measurement_result}.", 80, BLACK)
            render_centered("Bob applies corresponding quantum gates to recover the state.", 130, BLACK)
            render_centered("Choose the right correction below:", 180, YELLOW)

            correction_buttons = draw_buttons(["I", "X", "Z", "XZ"], 220)

        elif phase == "result":
            if result_msg == "Teleportation successful! Bob got |ψ>.":
                draw_bloch_sphere(alice_pos, "Alice", alice_bloch, collapsed=True)
                draw_bloch_sphere(bob_pos, "Bob", alice_bloch, collapsed =True)

                if entangled:
                    pygame.draw.line(screen, RED, alice_pos, bob_pos, 4)


            render_centered("Teleportation Result", 120, YELLOW if teleport_success else RED)
            render_centered(result_msg, 180, GREEN if teleport_success else RED)
            render_centered("Click anywhere to restart.", 240, BLACK)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
