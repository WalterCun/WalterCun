# scripts/validate_readme_urls.py
import re, requests
from pathlib import Path

def extract_urls(markdown_path: str) -> list[str]:
    """Extrae todas las URLs de imágenes y enlaces en un README"""
    content = Path(markdown_path).read_text(encoding="utf-8")
    # Patrones para img src y href
    patterns = [
        r'src="([^"]+)"',
        r'href="([^"]+)"'
    ]
    urls = []
    for pattern in patterns:
        urls.extend(re.findall(pattern, content))
    return [u.strip() for u in urls if u.startswith('http') and 'github' not in u]

def validate_url(url: str) -> bool:
    """Verifica si una URL responde con 200"""
    try:
        # Headers para evitar bloqueos por user-agent
        headers = {'User-Agent': 'Mozilla/5.0 (README Validator)'}
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

if __name__ == "__main__":
    readme = "README.md"
    print(f"🔍 Validando URLs en {readme}...")
    urls = extract_urls(readme)
    
    broken = []
    for url in urls:
        if not validate_url(url):
            broken.append(url)
            print(f"❌ {url}")
    
    if broken:
        print(f"\n⚠️ {len(broken)} URLs rotas detectadas. Revisar antes de publicar.")
        exit(1)
    else:
        print(f"✅ Todas las {len(urls)} URLs están activas.")