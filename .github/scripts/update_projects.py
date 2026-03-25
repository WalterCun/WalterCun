# .github/scripts/update_projects.py
"""
🔄 Script de Actualización Automática de Proyectos Destacados

Este script:
1. Consulta la GitHub API para obtener repositorios pinned
2. Extrae metadata: nombre, descripción, lenguaje, stars, últimos commits
3. Genera tabla Markdown formateada
4. Actualiza README.md y i18n/README.en.md entre marcadores

🔧 Configuración:
• GITHUB_TOKEN: Token de GitHub (automático en Actions)
• USERNAME: Usuario de GitHub (ej: WalterCun)
• FORCE_UPDATE: Forzar actualización incluso sin cambios

📅 Ejecución: Mensual (día 1) + Manual desde GitHub Actions UI
"""

import os
import re
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
USERNAME = os.getenv("USERNAME", "WalterCun")
FORCE_UPDATE = os.getenv("FORCE_UPDATE", "false").lower() == "true"

# Marcadores en el README para identificar dónde insertar proyectos
MARKERS = {
    "es": {"start": "<!-- projects-start-es -->", "end": "<!-- projects-end-es -->"},
    "en": {"start": "<!-- projects-start-en -->", "end": "<!-- projects-end-en -->"}
}

# Archivos a actualizar
FILES = {
    "es": "README.md",
    "en": "i18n/README.en.md"
}

# Límite de proyectos a mostrar
MAX_PROJECTS = 6

# ═══════════════════════════════════════════════════════════════════════
# CLASES Y FUNCIONES
# ═══════════════════════════════════════════════════════════════════════

class GitHubAPI:
    """Cliente simplificado para GitHub API"""
    
    def __init__(self, token: str, username: str):
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "WalterCun-README-Bot/1.0"
        }
    
    def get_pinned_repositories(self) -> List[Dict]:
        """
        Obtiene repositorios pinned del usuario
        
        Returns:
            Lista de diccionarios con metadata de cada repo
        """
        query = f"""
        query {{
          user(login: "{self.username}") {{
            pinnedItems(first: {MAX_PROJECTS}, types: REPOSITORY) {{
              nodes {{
                ... on Repository {{
                  name
                  description
                  url
                  primaryLanguage {{
                    name
                    color
                  }}
                  stargazerCount
                  forkCount
                  updatedAt
                  homepageUrl
                  topics
                }}
              }}
            }}
          }}
        }}
        """
        
        response = requests.post(
            f"{self.base_url}/graphql",
            headers=self.headers,
            json={"query": query}
        )
        
        if response.status_code == 200:
            data = response.json()
            pinned = data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
            return pinned
        else:
            print(f"⚠️ Error fetching pinned repos: {response.status_code}")
            return []
    
    def get_repository_stats(self, repo_name: str) -> Dict:
        """
        Obtiene estadísticas adicionales de un repositorio
        
        Args:
            repo_name: Nombre del repositorio
        
        Returns:
            Diccionario con commits recientes, contribuidores, etc.
        """
        # Últimos commits
        commits_url = f"{self.base_url}/repos/{self.username}/{repo_name}/commits?per_page=5"
        commits_response = requests.get(commits_url, headers=self.headers)
        
        stats = {
            "recent_commits": 0,
            "last_commit_date": None
        }
        
        if commits_response.status_code == 200:
            commits = commits_response.json()
            stats["recent_commits"] = len(commits)
            if commits:
                stats["last_commit_date"] = commits[0].get("commit", {}).get("committer", {}).get("date", "")
        
        return stats


class ProjectCard:
    """Generador de tarjetas de proyecto en Markdown"""
    
    @staticmethod
    def get_language_badge(language: Optional[Dict]) -> str:
        """Genera badge del lenguaje principal"""
        if not language or not language.get("name"):
            return "![Language](https://img.shields.io/badge/code-grey?style=flat-square)"
        
        name = language["name"]
        color = language.get("color", "#777777").lstrip("#")
        return f"![{name}](https://img.shields.io/badge/{name}-{color}?style=flat-square&logo=github)"
    
    @staticmethod
    def get_status_badge(updated_at: str) -> str:
        """Determina estado basado en última actualización"""
        if not updated_at:
            return "🔴 Inactivo"
        
        from datetime import datetime, timedelta
        last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        days_since = (datetime.now(last_update.tzinfo) - last_update).days
        
        if days_since <= 30:
            return "🟢 Activo"
        elif days_since <= 90:
            return "🟡 Mantenimiento"
        else:
            return "🔴 Inactivo"
    
    @classmethod
    def generate(cls, repo: Dict, stats: Dict) -> str:
        """
        Genera fila de tabla Markdown para un proyecto
        
        Args:
            repo: Metadata del repositorio desde GitHub API
            stats: Estadísticas adicionales
        
        Returns:
            String con fila de tabla Markdown
        """
        name = repo.get("name", "Unknown")
        description = repo.get("description", "Sin descripción") or "Sin descripción"
        url = repo.get("url", "#")
        language = repo.get("primaryLanguage")
        stars = repo.get("stargazerCount", 0)
        forks = repo.get("forkCount", 0)
        updated_at = repo.get("updatedAt", "")
        homepage = repo.get("homepageUrl", "")
        topics = repo.get("topics", [])
        
        # Truncar descripción si es muy larga
        if len(description) > 80:
            description = description[:77] + "..."
        
        # Badges
        lang_badge = cls.get_language_badge(language)
        status_badge = cls.get_status_badge(updated_at)
        stars_badge = f"⭐ {stars}" if stars > 0 else ""
        forks_badge = f"🍴 {forks}" if forks > 0 else ""
        
        # Links adicionales
        demo_link = f" | [🌐 Demo]({homepage})" if homepage else ""
        
        # Topics como badges pequeños
        topics_str = ""
        for topic in topics[:3]:  # Máximo 3 topics
            topics_str += f" \`{topic}\`"
        
        return f"| [{name}]({url}) | {description} | {lang_badge} {status_badge} {stars_badge} {forks_badge}{demo_link} |"


class ReadmeUpdater:
    """Actualiza secciones específicas del README entre marcadores"""
    
    def __init__(self, file_path: str, lang: str):
        self.file_path = file_path
        self.lang = lang
        self.markers = MARKERS[lang]
    
    def read(self) -> str:
        """Lee el contenido del archivo README"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ Archivo no encontrado: {self.file_path}")
            return ""
    
    def write(self, content: str) -> bool:
        """Escribe contenido al archivo README"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ Error escribiendo archivo: {e}")
            return False
    
    def update_projects_section(self, projects_table: str) -> bool:
        """
        Actualiza la sección de proyectos entre marcadores
        
        Args:
            projects_table: Tabla Markdown generada con proyectos
        
        Returns:
            True si se actualizó correctamente
        """
        content = self.read()
        
        if not content:
            return False
        
        # Patrón para encontrar sección entre marcadores
        pattern = re.compile(
            f"{re.escape(self.markers['start'])}.*?{re.escape(self.markers['end'])}",
            re.DOTALL
        )
        
        # Nueva sección completa
        new_section = f"""{self.markers['start']}

{projects_table}

<!-- Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} -->
{self.markers['end']}"""
        
        # Reemplazar si existe, o agregar al final si no existen marcadores
        if pattern.search(content):
            new_content = pattern.sub(new_section, content)
        else:
            # Agregar antes del footer si no existen marcadores
            footer_marker = "<!-- 🎨 Footer -->"
            if footer_marker in content:
                new_content = content.replace(footer_marker, f"{new_section}\n\n{footer_marker}")
            else:
                new_content = content + f"\n\n{new_section}\n"
        
        return self.write(new_content)


# ═══════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Ejecuta el proceso completo de actualización"""
    
    print("=" * 60)
    print("🔄 AUTO-UPDATE PROJECTS SECTION")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Usuario: {USERNAME}")
    print(f"🔧 Force Update: {FORCE_UPDATE}")
    print("=" * 60)
    
    # Validar token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN no configurado")
        exit(1)
    
    # Inicializar cliente GitHub API
    gh = GitHubAPI(GITHUB_TOKEN, USERNAME)
    
    # Obtener repositorios pinned
    print("\n📌 Obteniendo repositorios pinned...")
    pinned_repos = gh.get_pinned_repositories()
    
    if not pinned_repos:
        print("⚠️ No se encontraron repositorios pinned")
        exit(0)
    
    print(f"✅ {len(pinned_repos)} repositorios encontrados")
    
    # Generar tabla de proyectos (ESPAÑOL)
    print("\n📝 Generando tabla de proyectos (Español)...")
    projects_header_es = """<!-- projects-start-es -->

| 📦 Proyecto | 📋 Descripción | 🛠️ Stack & Estado |
|-------------|----------------|-------------------|"""
    
    projects_rows_es = ""
    for repo in pinned_repos:
        stats = gh.get_repository_stats(repo["name"])
        row = ProjectCard.generate(repo, stats)
        projects_rows_es += f"\n{row}"
    
    projects_footer_es = """
> 💡 *Proyectos fijados manualmente en GitHub → "Customize your pins"*
> 🔄 *Actualización automática mensual vía GitHub Actions*

<!-- projects-end-es -->"""
    
    projects_table_es = projects_header_es + projects_rows_es + projects_footer_es
    
    # Generar tabla de proyectos (INGLÉS)
    print("\n📝 Generating projects table (English)...")
    projects_header_en = """<!-- projects-start-en -->

| 📦 Project | 📋 Description | 🛠️ Stack & Status |
|------------|----------------|-------------------|"""
    
    # Traducciones básicas para la tabla
    translations = {
        "Sin descripción": "No description",
        "🟢 Activo": "🟢 Active",
        "🟡 Mantenimiento": "🟡 Maintenance",
        "🔴 Inactivo": "🔴 Inactive",
        "Proyectos fijados manualmente": "Projects pinned manually",
        "Actualización automática mensual": "Monthly auto-update"
    }
    
    projects_rows_en = projects_rows_es
    for es, en in translations.items():
        projects_rows_en = projects_rows_en.replace(es, en)
    
    projects_footer_en = """
> 💡 *Projects pinned manually on GitHub → "Customize your pins"*
> 🔄 *Monthly auto-update via GitHub Actions*

<!-- projects-end-en -->"""
    
    projects_table_en = projects_header_en + projects_rows_en + projects_footer_en
    
    # Actualizar README.md (Español)
    print("\n✏️ Actualizando README.md...")
    updater_es = ReadmeUpdater(FILES["es"], "es")
    updated_es = updater_es.update_projects_section(projects_table_es)
    print(f"{'✅' if updated_es else '❌'} README.md: {'Actualizado' if updated_es else 'Fallido'}")
    
    # Actualizar i18n/README.en.md (Inglés)
    print("\n✏️ Updating i18n/README.en.md...")
    updater_en = ReadmeUpdater(FILES["en"], "en")
    updated_en = updater_en.update_projects_section(projects_table_en)
    print(f"{'✅' if updated_en else '❌'} README.en.md: {'Updated' if updated_en else 'Failed'}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE ACTUALIZACIÓN")
    print("=" * 60)
    print(f"📁 Archivos actualizados: {sum([updated_es, updated_en])}/2")
    print(f"📦 Proyectos procesados: {len(pinned_repos)}")
    print(f"⏰ Próxima ejecución: {datetime.now().replace(day=1).strftime('%Y-%m-%d')} (mensual)")
    print("=" * 60)
    
    # Exit code para GitHub Actions
    if updated_es and updated_en:
        print("\n✅ Actualización completada exitosamente")
        exit(0)
    else:
        print("\n⚠️ Actualización parcial o fallida")
        exit(1)


if __name__ == "__main__":
    main()