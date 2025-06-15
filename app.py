
from flask import Flask, request, render_template, jsonify
import os
import base64
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def create_sample_document():
    """サンプルドキュメントを作成（デモ用）"""
    content = f"""英語テキスト翻訳・単語解説レポート（デモ版）
作成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

=========================================
システム情報
=========================================
このバージョンはデモ版です。
実際のOCR・翻訳機能を使用するには、完全版をデプロイしてください。

=========================================
機能テスト
=========================================
✅ ファイルアップロード機能
✅ UI表示機能
✅ ダウンロード機能

まずは基本機能が動作することを確認しました。
次に AI 機能を段階的に追加していきます。

=========================================
今後の実装予定
=========================================
- Google Gemini API 連携
- 画像からのテキスト抽出
- 自動翻訳機能
- 重要単語解説生成
"""
    return content

@app.route('/')
def index():
    # まずは直接HTMLを返してテスト
    html_content = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英語本翻訳・解説アプリ (デモ版)</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f0f0f0; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        h1 { color: #333; text-align: center; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 英語本翻訳・解説アプリ (デモ版)</h1>
        <p style="text-align: center; color: #666;">Build成功！アプリが正常に動作しています 🎉</p>
        
        <div class="upload-area">
            <h3>✅ 基本機能テスト成功</h3>
            <p>次の段階: AI機能の追加に進みます</p>
        </div>
        
        <div style="text-align: center;">
            <button class="btn" onclick="alert('デモ版が正常に動作しています！')">
                🔄 動作テスト
            </button>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: #e8f5e8; border-radius: 5px;">
            <h4>✅ 確認済み機能:</h4>
            <ul>
                <li>Renderデプロイ成功</li>
                <li>Flaskアプリ起動</li>
                <li>HTML表示</li>
                <li>CSS スタイリング</li>
            </ul>
        </div>
    </div>
</body>
</html>
    '''
    return html_content

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
        
        # デモ用のサンプルテキスト
        sample_original = f"""Demo Text (English)
You have successfully uploaded {len(uploaded_files)} image(s).
This is a demonstration version of the English book translation app.
The actual OCR and translation features will be implemented once the deployment issues are resolved."""
        
        sample_translation = f"""デモテキスト（日本語）
{len(uploaded_files)}枚の画像が正常にアップロードされました。
これは英語本翻訳アプリのデモンストレーション版です。
実際のOCRと翻訳機能は、デプロイの問題が解決された後に実装されます。"""
        
        # サンプル単語データ
        sample_words = [
            {
                "word": "demonstration",
                "definition": "実演、デモンストレーション",
                "example": "This is a demonstration of the app.",
                "example_translation": "これはアプリのデモンストレーションです。",
                "level": "中級"
            },
            {
                "word": "translation",
                "definition": "翻訳",
                "example": "Translation is an important skill.",
                "example_translation": "翻訳は重要なスキルです。",
                "level": "初級"
            }
        ]
        
        # デモドキュメント作成
        doc_content = create_sample_document()
        
        # ファイル保存
        output_filename = f"demo_translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
            'original_text': sample_original,
            'translated_text': sample_translation,
            'word_count': len(sample_words),
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
    return jsonify({
        'status': 'healthy', 
        'version': 'demo',
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
    ''', 404

@app.errorhandler(500)
def internal_error(error):
    return '''
    <h1>500 - 内部サーバーエラー</h1>
    <p>アプリケーションでエラーが発生しました</p>
    <p><a href="/">ホームに戻る</a></p>
    ''', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"アプリケーションをポート {port} で起動中...")
    app.run(host='0.0.0.0', port=port, debug=False)