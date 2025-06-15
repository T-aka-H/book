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
    return render_template('index.html')

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
    return jsonify({'status': 'healthy', 'version': 'demo'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)