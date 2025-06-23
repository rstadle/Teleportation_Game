## Module Imports
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_histogram
from qiskit.primitives import StatevectorSampler

def noisy_simulator(qc):
    # Use fake noisy backend
    fake_backend = FakeManilaV2()
    noise_model = NoiseModel.from_backend(fake_backend)
    simulator = AerSimulator(noise_model=noise_model)

    # Transpile circuit
    qc_t = transpile(qc, simulator)
    # Run simulation
    shots = 1024
    # Note: shots is set to 1024, but can be adjusted as needed.
    job = simulator.run(qc_t, shots=shots)
    result = job.result()
    counts = result.get_counts()
    return counts, shots

def ideal_simulator(qc):
    """
    Simulate the quantum circuit on the ideal (noise-free) Aer simulator.
    """
    simulator = AerSimulator()
    qc_t = transpile(qc, simulator)
    shots = 1024  # Number of shots for the simulation
    # Note: shots is set to 1024, but can be adjusted as needed.
    job = simulator.run(qc_t, shots=shots)
    result = job.result()
    counts = result.get_counts()
    return counts, shots