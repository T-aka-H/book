from flask import Flask, request, jsonify
import os
import base64
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Gemini API設定（環境変数から取得）
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def extract_text_with_gemini_api(image_path):
    """Gemini APIを直接使用して画像からテキストを抽出"""
    if not GEMINI_API_KEY:
        return "APIキーが設定されていません"
    
    try:
        # 画像をbase64にエンコード
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Gemini API エンドポイント
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        # リクエストペイロード
        payload = {
            "contents": [{
                "parts": [
                    {"text": "この画像から英語のテキストを正確に抽出してください。レイアウトや改行を可能な限り保持し、読みやすい形で出力してください。テキストのみを返してください。"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text.strip()
        
        return f"APIエラー: {response.status_code}"
    
    except Exception as e:
        return f"OCRエラー: {str(e)}"

def translate_text_with_gemini_api(text):
    """Gemini APIを使用してテキストを翻訳"""
    if not GEMINI_API_KEY:
        return "APIキーが設定されていません"
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""以下の英語テキストを自然で読みやすい日本語に翻訳してください。
文学的な表現や専門用語も適切に翻訳し、原文の意味とニュアンスを保持してください。

英語テキスト:
{text}"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                translation = result['candidates'][0]['content']['parts'][0]['text']
                return translation.strip()
        
        return f"翻訳APIエラー: {response.status_code}"
    
    except Exception as e:
        return f"翻訳エラー: {str(e)}"

def extract_words_with_gemini_api(text):
    """Gemini APIを使用して重要単語を抽出"""
    if not GEMINI_API_KEY:
        return []
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""以下の英語テキストから、学習に重要な単語を最大20個選択し、
各単語について以下の形式でJSONで返してください：

{{
    "words": [
        {{
            "word": "単語",
            "definition": "日本語での意味・定義",
            "example": "その単語を使った例文（英語）",
            "example_translation": "例文の日本語訳",
            "level": "初級/中級/上級"
        }}
    ]
}}

英語テキスト:
{text[:1500]}"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # JSONを抽出
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                else:
                    json_text = response_text
                
                data = json.loads(json_text)
                return data.get("words", [])
        
        return []
    
    except Exception as e:
        print(f"単語抽出エラー: {e}")
        return []

def extract_grammar_patterns_with_gemini_api(text):
    """Gemini APIを使用して構文パターンを抽出・解説"""
    if not GEMINI_API_KEY:
        return []
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""以下の英語テキストから、重要な文法・構文パターンを最大15個抽出し、
各パターンについて以下の形式でJSONで返してください：

{{
    "grammar_patterns": [
        {{
            "pattern": "構文パターン名（例：as...as構文）",
            "example_sentence": "テキストから該当する文を抜粋",
            "structure": "構文の構造（例：as + 形容詞 + as + 主語 + 動詞）",
            "meaning": "この構文の意味・用法",
            "level": "初級/中級/上級",
            "other_examples": "他の例文2-3個"
        }}
    ]
}}

抽出対象の構文パターン例：
- 比較構文（as...as, more...than など）
- 関係代名詞（who, which, that など）
- 分詞構文（現在分詞、過去分詞）
- 仮定法（if節、would など）
- 倒置構文
- 強調構文（it is...that など）
- 同格構文
- 省略構文
- 慣用表現

英語テキスト:
{text[:1800]}"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                response_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # JSONを抽出
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                else:
                    json_text = response_text
                
                data = json.loads(json_text)
                return data.get("grammar_patterns", [])
        
        return []
    
    except Exception as e:
        print(f"構文解析エラー: {e}")
        return []

def create_text_document(original_text, translated_text, important_words, grammar_patterns):
    """テキストドキュメントを作成"""
    content = f"""英語テキスト翻訳・構文・単語解説レポート
作成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

=========================================
原文（英語）
=========================================
{original_text}

=========================================
翻訳（日本語）
=========================================
{translated_text}

=========================================
文法・構文解説（{len(grammar_patterns)}パターン）
=========================================

"""
    
    for i, pattern in enumerate(grammar_patterns, 1):
        content += f"""
{i}. {pattern.get("pattern", "")}
────────────────────────────────────────
例文: {pattern.get("example_sentence", "")}
構造: {pattern.get("structure", "")}
意味・用法: {pattern.get("meaning", "")}
レベル: {pattern.get("level", "")}
他の例文: {pattern.get("other_examples", "")}

"""

    content += f"""
=========================================
重要単語解説（{len(important_words)}語）
=========================================

"""
    
    for i, word_info in enumerate(important_words, 1):
        content += f"""
{i}. {word_info.get("word", "")}
────────────────────────────────────────
意味: {word_info.get("definition", "")}
レベル: {word_info.get("level", "")}
例文: {word_info.get("example", "")}
例文翻訳: {word_info.get("example_translation", "")}

"""
    
    return content

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except:
        # テンプレートが見つからない場合の緊急対応
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英語本翻訳・解説アプリ</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Yu Gothic', 'Hiragino Sans', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 40px; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1); backdrop-filter: blur(10px); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; font-size: 2.5em; font-weight: 300; background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .upload-area { border: 3px dashed #667eea; border-radius: 15px; padding: 60px 20px; text-align: center; cursor: pointer; transition: all 0.3s ease; margin-bottom: 30px; background: rgba(102, 126, 234, 0.05); }
        .upload-area:hover { border-color: #764ba2; background: rgba(102, 126, 234, 0.1); transform: translateY(-2px); }
        .upload-area.dragover { border-color: #764ba2; background: rgba(102, 126, 234, 0.15); }
        .upload-icon { font-size: 4em; margin-bottom: 20px; color: #667eea; }
        .upload-text { font-size: 1.2em; color: #555; margin-bottom: 15px; }
        .upload-subtext { color: #888; font-size: 0.9em; }
        #file-input { display: none; }
        .btn { background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; padding: 15px 30px; font-size: 1.1em; border-radius: 25px; cursor: pointer; transition: all 0.3s ease; margin: 10px; text-decoration: none; display: inline-block; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .file-list { margin: 20px 0; background: rgba(102, 126, 234, 0.05); border-radius: 10px; padding: 20px; max-height: 200px; overflow-y: auto; }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(102, 126, 234, 0.1); }
        .file-item:last-child { border-bottom: none; }
        .file-name { font-weight: 500; color: #333; }
        .file-size { color: #666; font-size: 0.9em; }
        .remove-file { background: #ff6b6b; color: white; border: none; border-radius: 50%; width: 25px; height: 25px; cursor: pointer; font-size: 12px; transition: all 0.3s ease; }
        .remove-file:hover { background: #ff5252; transform: scale(1.1); }
        .progress-container { display: none; margin: 20px 0; }
        .progress-bar { width: 100%; height: 20px; background: rgba(102, 126, 234, 0.1); border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(45deg, #667eea, #764ba2); width: 0%; transition: width 0.3s ease; border-radius: 10px; }
        .status-message { text-align: center; margin: 20px 0; padding: 15px; border-radius: 10px; font-weight: 500; }
        .status-success { background: rgba(76, 175, 80, 0.1); color: #2e7d32; border: 1px solid rgba(76, 175, 80, 0.3); }
        .status-error { background: rgba(244, 67, 54, 0.1); color: #c62828; border: 1px solid rgba(244, 67, 54, 0.3); }
        .results { display: none; margin-top: 30px; padding: 30px; background: rgba(102, 126, 234, 0.05); border-radius: 15px; }
        .result-section { margin-bottom: 25px; }
        .result-title { font-size: 1.3em; font-weight: 600; color: #333; margin-bottom: 10px; border-bottom: 2px solid #667eea; padding-bottom: 5px; }
        .result-content { background: white; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea; max-height: 200px; overflow-y: auto; line-height: 1.6; }
        .download-section { text-align: center; padding: 20px; background: rgba(76, 175, 80, 0.1); border-radius: 10px; margin-top: 20px; }
        .word-count { display: inline-block; background: #667eea; color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; margin-left: 10px; }
        .api-status { background: rgba(255, 193, 7, 0.1); border: 1px solid rgba(255, 193, 7, 0.3); color: #f57c00; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .loading-spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(255, 255, 255, 0.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; margin-right: 10px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (max-width: 768px) { .container { padding: 20px; margin: 10px; } h1 { font-size: 2em; } .upload-area { padding: 40px 15px; } .btn { padding: 12px 25px; font-size: 1em; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 英語本翻訳・解説アプリ</h1>
        
        <div id="api-status" class="api-status" style="display: none;">
            ⚠️ Gemini APIキーが設定されていません。管理者に連絡してください。
        </div>
        
        <div class="upload-area" onclick="document.getElementById('file-input').click()">
            <div class="upload-icon">📸</div>
            <div class="upload-text">英語の本の写真をアップロード</div>
            <div class="upload-subtext">最大20枚まで対応 (PNG, JPG, JPEG, GIF, BMP)</div>
        </div>
        
        <input type="file" id="file-input" multiple accept="image/*">
        
        <div id="file-list" class="file-list" style="display: none;"></div>
        
        <div style="text-align: center;">
            <button id="process-btn" class="btn" onclick="processImages()" disabled>
                🔄 翻訳・解析開始
            </button>
            <button id="clear-btn" class="btn" onclick="clearFiles()" style="background: #ff6b6b;">
                🗑️ クリア
            </button>
        </div>
        
        <div id="progress" class="progress-container">
            <div class="progress-bar">
                <div id="progress-fill" class="progress-fill"></div>
            </div>
            <div id="status-text" style="text-align: center; margin-top: 10px; color: #666;">
                処理中...
            </div>
        </div>
        
        <div id="status-message" class="status-message" style="display: none;"></div>
        
        <div id="results" class="results">
            <div class="result-section">
                <div class="result-title">
                    📖 原文（英語）
                </div>
                <div id="original-text" class="result-content"></div>
            </div>
            
            <div class="result-section">
                <div class="result-title">
                    🇯🇵 翻訳（日本語）
                </div>
                <div id="translated-text" class="result-content"></div>
            </div>
            
            <div class="result-section">
                <div class="result-title">
                    📚 文法・構文解説
                    <span id="grammar-count" class="word-count"></span>
                </div>
                <div class="result-content">
                    重要な文法・構文パターンの詳細解説がレポートファイルに含まれています
                </div>
            </div>
            
            <div class="result-section">
                <div class="result-title">
                    📝 重要単語解説
                    <span id="word-count" class="word-count"></span>
                </div>
                <div class="result-content">
                    重要な単語の詳細解説がレポートファイルに含まれています
                </div>
            </div>
            
            <div class="download-section">
                <h3 style="margin-bottom: 15px; color: #2e7d32;">📄 ダウンロード</h3>
                <button id="download-btn" class="btn" style="background: #4caf50;">
                    💾 レポートをダウンロード
                </button>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        let resultData = null;

        // APIキーステータス確認
        window.addEventListener('load', function() {
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    if (data.api_key_status === 'missing') {
                        document.getElementById('api-status').style.display = 'block';
                    }
                })
                .catch(error => console.log('Health check failed:', error));
        });

        // ファイル入力の処理
        document.getElementById('file-input').addEventListener('change', function(e) {
            handleFiles(e.target.files);
        });

        // ドラッグ&ドロップ
        const uploadArea = document.querySelector('.upload-area');
        
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        function handleFiles(files) {
            const maxFiles = 20;
            const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp'];
            
            for (let file of files) {
                if (selectedFiles.length >= maxFiles) {
                    showStatus('最大20枚まで選択可能です', 'error');
                    break;
                }
                
                if (!allowedTypes.includes(file.type)) {
                    showStatus(`${file.name} は対応していないファイル形式です`, 'error');
                    continue;
                }
                
                if (selectedFiles.find(f => f.name === file.name)) {
                    continue; // 重複ファイルはスキップ
                }
                
                selectedFiles.push(file);
            }
            
            updateFileList();
            updateProcessButton();
        }

        function updateFileList() {
            const fileList = document.getElementById('file-list');
            
            if (selectedFiles.length === 0) {
                fileList.style.display = 'none';
                return;
            }
            
            fileList.style.display = 'block';
            fileList.innerHTML = '';
            
            const header = document.createElement('h4');
            header.textContent = `選択されたファイル (${selectedFiles.length}枚)`;
            header.style.marginBottom = '15px';
            fileList.appendChild(header);
            
            selectedFiles.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                const fileInfo = document.createElement('div');
                fileInfo.innerHTML = `
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                `;
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'remove-file';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = () => removeFile(index);
                
                fileItem.appendChild(fileInfo);
                fileItem.appendChild(removeBtn);
                fileList.appendChild(fileItem);
            });
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
            updateProcessButton();
        }

        function clearFiles() {
            selectedFiles = [];
            updateFileList();
            updateProcessButton();
            hideResults();
            hideStatus();
        }

        function updateProcessButton() {
            const processBtn = document.getElementById('process-btn');
            processBtn.disabled = selectedFiles.length === 0;
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function processImages() {
            if (selectedFiles.length === 0) return;
            
            const processBtn = document.getElementById('process-btn');
            const progressContainer = document.getElementById('progress');
            const progressFill = document.getElementById('progress-fill');
            const statusText = document.getElementById('status-text');
            
            // UI更新
            processBtn.disabled = true;
            processBtn.innerHTML = '<div class="loading-spinner"></div>処理中...';
            progressContainer.style.display = 'block';
            hideStatus();
            hideResults();
            
            try {
                // FormDataを作成
                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });
                
                // プログレス更新
                progressFill.style.width = '20%';
                statusText.textContent = 'ファイルをアップロード中...';
                
                // APIリクエスト
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                progressFill.style.width = '50%';
                statusText.textContent = 'AI処理中...';
                
                const data = await response.json();
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    statusText.textContent = '完了！';
                    
                    setTimeout(() => {
                        progressContainer.style.display = 'none';
                        showResults(data);
                        showStatus('処理が完了しました！', 'success');
                    }, 1000);
                    
                    resultData = data;
                } else {
                    throw new Error(data.error || 'エラーが発生しました');
                }
                
            } catch (error) {
                progressContainer.style.display = 'none';
                showStatus(`エラー: ${error.message}`, 'error');
                console.error('処理エラー:', error);
            } finally {
                processBtn.disabled = false;
                processBtn.innerHTML = '🔄 翻訳・解析開始';
            }
        }

        function showResults(data) {
            const results = document.getElementById('results');
            const originalText = document.getElementById('original-text');
            const translatedText = document.getElementById('translated-text');
            const wordCount = document.getElementById('word-count');
            const grammarCount = document.getElementById('grammar-count');
            const downloadBtn = document.getElementById('download-btn');
            
            originalText.textContent = data.original_text;
            translatedText.textContent = data.translated_text;
            wordCount.textContent = `${data.word_count}語`;
            grammarCount.textContent = `${data.grammar_count}パターン`;
            
            downloadBtn.onclick = () => downloadFile(data);
            
            results.style.display = 'block';
        }

        function hideResults() {
            document.getElementById('results').style.display = 'none';
            resultData = null;
        }

        function downloadFile(data) {
            try {
                // Base64データをBlobに変換
                const byteCharacters = atob(data.file_data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], {
                    type: 'text/plain; charset=utf-8'
                });
                
                // ダウンロードリンクを作成
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = data.filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                showStatus('ファイルのダウンロードを開始しました', 'success');
            } catch (error) {
                showStatus('ダウンロードエラーが発生しました', 'error');
                console.error('ダウンロードエラー:', error);
            }
        }

        function showStatus(message, type) {
            const statusMessage = document.getElementById('status-message');
            statusMessage.textContent = message;
            statusMessage.className = `status-message status-${type}`;
            statusMessage.style.display = 'block';
            
            if (type === 'success') {
                setTimeout(() => {
                    hideStatus();
                }, 5000);
            }
        }

        function hideStatus() {
            document.getElementById('status-message').style.display = 'none';
        }
    </script>
</body>
</html>"""

@app.route('/version')
def version_check():
    return jsonify({
        'version': 'latest-2024-06-15',
        'status': 'updated',
        'template_status': 'embedded',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    files = request.files.getlist('files')
    
    if len(files) > 20:
        return jsonify({'error': '最大20枚まで処理可能です'}), 400
    
    # 一時ディレクトリを作成
    temp_dir = tempfile.mkdtemp()
    uploaded_files = []
    
    try:
        # ファイルをアップロード
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(temp_dir, filename)
                file.save(filepath)
                uploaded_files.append(filepath)
        
        if not uploaded_files:
            return jsonify({'error': '有効な画像ファイルがありません'}), 400
        
        # OCR処理
        all_text = ""
        
        for image_path in uploaded_files:
            extracted_text = extract_text_with_gemini_api(image_path)
            if extracted_text and not extracted_text.startswith("APIエラー") and not extracted_text.startswith("OCRエラー"):
                all_text += extracted_text + "\n\n"
        
        if not all_text.strip():
            return jsonify({'error': 'テキストを抽出できませんでした'}), 400
        
        # 翻訳
        translated_text = translate_text_with_gemini_api(all_text)
        
        # 重要単語抽出
        important_words = extract_words_with_gemini_api(all_text)
        
        # 構文パターン抽出
        grammar_patterns = extract_grammar_patterns_with_gemini_api(all_text)
        
        # テキストドキュメント作成
        doc_content = create_text_document(all_text, translated_text, important_words, grammar_patterns)
        
        # ファイル保存
        output_filename = f"translation_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = os.path.join(temp_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        # ファイルをバイナリで読み込み
        with open(output_path, 'rb') as f:
            file_data = f.read()
        
        # 一時ファイル削除
        import shutil
        shutil.rmtree(temp_dir)
        
        # レスポンス
        return jsonify({
            'status': 'success',
            'original_text': all_text[:500] + '...' if len(all_text) > 500 else all_text,
            'translated_text': translated_text[:500] + '...' if len(translated_text) > 500 else translated_text,
            'word_count': len(important_words),
            'grammar_count': len(grammar_patterns),
            'download_url': f'/download/{output_filename}',
            'file_data': base64.b64encode(file_data).decode('utf-8'),
            'filename': output_filename
        })
    
    except Exception as e:
        # エラー時は一時ディレクトリを削除
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return jsonify({'error': f'処理中にエラーが発生しました: {str(e)}'}), 500

@app.route('/health')
def health_check():
    api_key_status = 'ok' if GEMINI_API_KEY else 'missing'
    return jsonify({
        'status': 'healthy', 
        'version': 'latest-production',
        'api_key_status': api_key_status,
        'message': 'アプリは正常に動作しています！',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/debug')
def debug_info():
    import sys
    return jsonify({
        'python_version': sys.version,
        'flask_working': True,
        'current_directory': os.getcwd(),
        'template_folder': app.template_folder,
        'gemini_api_configured': bool(GEMINI_API_KEY),
        'environment_vars': {
            'PORT': os.environ.get('PORT', 'Not Set'),
            'PYTHON_VERSION': os.environ.get('PYTHON_VERSION', 'Not Set')
        }
    })

@app.errorhandler(404)
def not_found(error):
    return '''
    <h1>404 - ページが見つかりません</h1>
    <p><a href="/">ホームに戻る</a></p>
    <p>デバッグ情報: <a href="/debug">/debug</a></p>
    <p>ヘルスチェック: <a href="/health">/health</a></p>
    <p>バージョン確認: <a href="/version">/version</a></p>
    ''', 404

@app.errorhandler(500)
def internal_error(error):
    return '''
    <h1>500 - 内部サーバーエラー</h1>
    <p>アプリケーションでエラーが発生しました</p>
    <p><a href="/">ホームに戻る</a></p>
    <p>ヘルスチェック: <a href="/health">/health</a></p>
    ''', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"アプリケーションをポート {port} で起動中...")
    print(f"Gemini API設定状況: {'✅ 設定済み' if GEMINI_API_KEY else '❌ 未設定'}")
    app.run(host='0.0.0.0', port=port, debug=False)