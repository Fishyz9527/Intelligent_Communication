using Newtonsoft.Json;
using System.Net.Http;
using System.Net.Http.Json;
using System.Windows;

namespace C_Sharp_file
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private const string BaseUrl = "http://localhost:8000/api";
        private readonly HttpClient _httpClient = new HttpClient();
        public MainWindow()
        {
            InitializeComponent();
            _httpClient.DefaultRequestHeaders.Accept.Clear();
            _httpClient.DefaultRequestHeaders.Accept.Add(
                new System.Net.Http.Headers.MediaTypeWithQualityHeaderValue("application/json"));
        }

        #region 语法检查按钮点击事件
        public class GrammarIssue
        {
            public int start { get; set; }
            public int end { get; set; }
            public required string message { get; set; }
            public required List<string> replacements { get; set; }
        }
        public class GrammarCheckResult
        {
            public required string original { get; set; }
            public required List<GrammarIssue> issues { get; set; }
        }
        private async void BtnCheck_Click(object sender, RoutedEventArgs e)
        {
            var inputText = txtInput.Text.Trim();
            if (string.IsNullOrWhiteSpace(inputText))
            {
                MessageBox.Show("请输入文本");
                return;
            }
            var request = new
            {
                text = inputText,
                language = "auto"
            };

            try
            {
                var response = await _httpClient.PostAsJsonAsync($"{BaseUrl}/grammar-check", request);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                var grammarResult = JsonConvert.DeserializeObject<GrammarCheckResult>(json);

                if (grammarResult.issues == null || grammarResult.issues.Count == 0)
                {
                    MessageBox.Show("未检测到语法问题！");
                }
                else
                {
                    lstIssues.ItemsSource = grammarResult.issues;
                    txtOutput.Text = JsonConvert.SerializeObject(grammarResult.issues, Formatting.Indented);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"语法检查失败：{ex.Message}");
            }
        }
        #endregion

        #region 翻译按钮点击事件
        private async void BtnTranslate_Click(object sender, RoutedEventArgs e)
        {
            var request = new
            {
                text = txtInput.Text,
                source_lang = "auto",
                target_lang = "en"
            };

            try
            {
                var response = await _httpClient.PostAsJsonAsync($"{BaseUrl}/translate", request);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                dynamic result = JsonConvert.DeserializeObject(json);

                txtOutput.Text = Convert.ToString(result.translated);
                lstIssues.ItemsSource = null;
            }

            catch (Exception ex)
            {
                MessageBox.Show($"翻译失败：{ex.Message}");
            }
        }
        #endregion

        #region 语言润色按钮点击事件
        private async void BtnPolish_Click(object sender, RoutedEventArgs e)
        {
            var request = new
            {
                text = txtInput.Text
            };
            try
            {
                var response = await _httpClient.PostAsJsonAsync($"{BaseUrl}/polish", request);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                dynamic result = JsonConvert.DeserializeObject(json);

                txtOutput.Text = Convert.ToString(result.polished);
                lstIssues.ItemsSource = null;
            }
            catch (HttpRequestException ex)
            {
                MessageBox.Show($"语言润色失败:{ex.Message}");

            }
        }
        #endregion

        private void ShowMessage(string msg)
        {
            MessageBox.Show(msg, "提示", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}
