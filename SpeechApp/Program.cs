using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using NAudio.Wave;

namespace SpeechApp;

class Program
{
    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("Usage: SpeechApp.exe <text> [voice_expr] [speed]");
            return;
        }

        string text = args[0];
        string voice = args.Length > 1 ? args[1] : "gideon";
        string speed = args.Length > 2 ? args[2] : "1.0";

        string pythonExe = @"C:\Miniforge\python.exe";
        string synthScript = @"C:\dev\speech-mcp-server\synth.py";

        if (!File.Exists(pythonExe) || !File.Exists(synthScript))
        {
            Console.WriteLine("Error: Python executable or synth.py not found.");
            return;
        }

        var psi = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"\"{synthScript}\" \"{text.Replace("\"", "\\\"")}\" \"{voice}\" \"{speed}\" --raw-pcm",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.Latin1
        };

        Console.WriteLine($"[WASAPI Engine] Synthesizing: {text}");

        using var process = new Process { StartInfo = psi };
        using var ms = new MemoryStream();
        process.Start();

        // Read binary stream asynchronously from Python stdout into memory
        var copyTask = process.StandardOutput.BaseStream.CopyToAsync(ms);
        process.WaitForExit();
        copyTask.Wait();

        byte[] pcmData = ms.ToArray();

        if (pcmData.Length == 0)
        {
            string err = process.StandardError.ReadToEnd();
            Console.WriteLine($"Synthesis Error: {err}");
            return;
        }

        // Play raw 24kHz 16-bit Mono PCM directly via WASAPI Out in RAM
        PlayWasapiPcmStream(pcmData, sampleRate: 24000, bitsPerSample: 16, channels: 1);
    }

    private static void PlayWasapiPcmStream(byte[] pcmBytes, int sampleRate, int bitsPerSample, int channels)
    {
        try
        {
            var waveFormat = new WaveFormat(sampleRate, bitsPerSample, channels);
            using var waveProvider = new RawSourceWaveStream(new MemoryStream(pcmBytes), waveFormat);
            using var wasapiOut = new WasapiOut(NAudio.CoreAudioApi.AudioClientShareMode.Shared, 50);

            wasapiOut.Init(waveProvider);
            wasapiOut.Play();

            while (wasapiOut.PlaybackState == PlaybackState.Playing)
            {
                Thread.Sleep(20);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"WASAPI Playback Error: {ex.Message}");
        }
    }
}
