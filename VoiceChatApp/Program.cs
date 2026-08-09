using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Speech.Recognition;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using NAudio.Wave;

namespace VoiceChatApp;

class Program
{
    private static readonly string PythonExe = @"C:\Miniforge\python.exe";
    private static readonly string SynthScript = @"C:\dev\speech-mcp-server\synth.py";
    private static SpeechRecognitionEngine? _recognizer;
    private static bool _isSpeaking = false;
    private static WaveInEvent? _waveIn;
    private static MemoryStream? _audioBuffer;

    static void Main(string[] args)
    {
        Console.WriteLine("==================================================");
        Console.WriteLine("  METROPOLIS NAUDIO HARDWARE MIC VOICE CHAT");
        Console.WriteLine("==================================================");

        try
        {
            // List available recording devices
            Console.WriteLine("Available Recording Devices:");
            for (int n = 0; n < WaveIn.DeviceCount; n++)
            {
                var caps = WaveIn.GetCapabilities(n);
                Console.WriteLine($"  [{n}] {caps.ProductName}");
            }

            _recognizer = new SpeechRecognitionEngine();
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SpeechRecognized += Recognizer_SpeechRecognized;
            _recognizer.SpeechHypothesized += (s, e) => {
                if (!_isSpeaking && e.Result != null && e.Result.Confidence > 0.15)
                {
                    Console.Write($"\r[Hearing]: {e.Result.Text}                      ");
                }
            };
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.RecognizeAsync(RecognizeMode.Multiple);
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("\n[SUCCESS] Windows System.Speech bound to default microphone!");
            Console.ResetColor();
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"[MIC ERROR]: {ex.Message}");
            Console.ResetColor();
        }

        Console.WriteLine("\n[System Listening... Speak clearly into your mic. Press CTRL+C to exit]");
        while (true)
        {
            System.Threading.Thread.Sleep(500);
        }
    }

    private static async void Recognizer_SpeechRecognized(object? sender, SpeechRecognizedEventArgs e)
    {
        if (_isSpeaking) return;
        if (e.Result == null || string.IsNullOrWhiteSpace(e.Result.Text)) return;
        if (e.Result.Confidence < 0.20) return; // Low threshold so it catches normal speech

        string heardText = e.Result.Text;
        Console.ForegroundColor = ConsoleColor.Yellow;
        Console.WriteLine($"\n\n>>> [MIC CAPTURED]: \"{heardText}\" (Confidence: {e.Result.Confidence:P0})");
        Console.ResetColor();

        _isSpeaking = true;
        try
        {
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("[Cloudflare Edge Llama-3 responding...]");
            Console.ResetColor();

            string aiResponse = await QueryEdgeLlamaAsync(heardText);

            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine($"[Gideon]: {aiResponse}");
            Console.ResetColor();

            SpeakWasapi(aiResponse, "gideon");
        }
        finally
        {
            _isSpeaking = false;
        }
    }

    private static async Task<string> QueryEdgeLlamaAsync(string prompt)
    {
        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
            var payload = new { prompt = prompt };
            var json = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await client.PostAsync("https://dgc-edge-gate.dondlingergc.workers.dev/ai", content);
            if (response.IsSuccessStatusCode)
            {
                var resBody = await response.Content.ReadAsStringAsync();
                using var doc = JsonDocument.Parse(resBody);
                if (doc.RootElement.TryGetProperty("response", out var respProp))
                {
                    return respProp.GetString() ?? "No response string received.";
                }
                return resBody;
            }
        }
        catch
        {
            // Offline fallback
        }

        return $"Received your spoken command: {prompt}. MetroNode systems standing by.";
    }

    private static void SpeakWasapi(string text, string persona)
    {
        if (!File.Exists(PythonExe) || !File.Exists(SynthScript)) return;

        var psi = new ProcessStartInfo
        {
            FileName = PythonExe,
            Arguments = $"\"{SynthScript}\" \"{text.Replace("\"", "\\\"")}\" \"{persona}\" \"1.0\" --raw-pcm",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        using var process = new Process { StartInfo = psi };
        process.Start();

        var waveFormat = new WaveFormat(22050, 16, 1);
        using var waveOut = new WasapiOut();
        var bufferedWaveProvider = new BufferedWaveProvider(waveFormat)
        {
            BufferDuration = TimeSpan.FromSeconds(30),
            DiscardOnBufferOverflow = true
        };

        waveOut.Init(bufferedWaveProvider);
        waveOut.Play();

        byte[] buffer = new byte[4096];
        int bytesRead;

        while ((bytesRead = process.StandardOutput.BaseStream.Read(buffer, 0, buffer.Length)) > 0)
        {
            bufferedWaveProvider.AddSamples(buffer, 0, bytesRead);
        }

        while (bufferedWaveProvider.BufferedBytes > 0 || process.HasExited == false)
        {
            System.Threading.Thread.Sleep(50);
        }

        System.Threading.Thread.Sleep(200);
        waveOut.Stop();
    }
}
