# Cambios

## 0.2.0
- Muestreo adaptativo de fotogramas (modo `smart`, por defecto): guarda un
  fotograma cada vez que la imagen cambia, incluidas líneas finas y textos
  pequeños, más uno de control cada ≤5 s.
- Whisper en GPU NVIDIA con `large-v3-turbo` (cuBLAS/cuDNN vía pip, sin CUDA
  Toolkit) y paso automático a CPU si la GPU falla.
- Windows: instalador desatendido (`instalar_todo.bat`) con Python 3.12, ffmpeg y Deno.
- Audio decodificado sin PyAV (evita fallos de versiones nuevas).
- Prueba automática y CI.

## 0.1.0
- Primera versión: hojas de fotogramas, transcripción, cortes de escena, zoom y Gemini opcional.
