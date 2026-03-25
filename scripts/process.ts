#!/usr/bin/env node

/**
 * 🔄 GitHub Profile README Auto-Updater
 * Fetches featured repositories and updates README.md dynamically
 * 
 * @author Walter Cun
 * @license MIT
 */

import { Octokit } from '@octokit/rest';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

// ─────────────────────────────────────────────────────────────
// 🔧 Configuración
// ─────────────────────────────────────────────────────────────

const CONFIG = {
  username: process.env.GITHUB_USERNAME || 'WalterCun',
  token: process.env.GITHUB_TOKEN || '',
  readmePath: 'README.md',
  targetTags: ['showcase', 'featured', 'project'],
  maxProjects: 6,
  sortBy: 'updated' as const, // 'updated' | 'stars' | 'name'
} as const;

// ─────────────────────────────────────────────────────────────
// 📦 Interfaces de Tipo
// ─────────────────────────────────────────────────────────────

interface GitHubRepo {
  name: string;
  description: string | null;
  html_url: string;
  stargazers_count: number;
  forks_count: number;
  language: string | null;
  topics: string[];
  visibility: 'public' | 'private' | 'internal';
  fork: boolean;
  updated_at: string;
  created_at: string;
}

interface ProjectCard {
  name: string;
  description: string;
  url: string;
  stars: number;
  forks: number;
  language: string;
  lastUpdate: string;
}

// ─────────────────────────────────────────────────────────────
// 🛠️ Funciones Auxiliares
// ─────────────────────────────────────────────────────────────

/**
 * Formatea una fecha ISO a formato legible en español
 */
function formatDateES(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Trunca texto a longitud máxima con ellipsis
 */
function truncate(text: string | null, maxLength: number = 120): string {
  if (!text) return 'Sin descripción disponible.';
  return text.length > maxLength 
    ? text.substring(0, maxLength).trim() + '...' 
    : text;
}

/**
 * Genera HTML para una tarjeta de proyecto
 */
function generateProjectCard(project: ProjectCard): string {
  const langBadge = project.language 
    ? `<img src="https://img.shields.io/badge/${encodeURIComponent(project.language)}-58A6FF?style=flat-square&logo=github&logoColor=white" alt="${project.language}"/>`
    : '';
  
  return `
<div style="display:inline-block; width:48%; margin:1%; padding:14px; border:1px solid #30363d; border-radius:8px; background:#161b22; vertical-align:top; min-height:140px;">
  <h4 style="margin:0 0 8px 0; font-size:16px;">
    <a href="${project.url}" style="color:#58a6ff; text-decoration:none; font-weight:600;">
      📦 ${project.name}
    </a>
  </h4>
  <p style="margin:0 0 10px 0; font-size:13px; color:#8b949e; line-height:1.4;">
    ${truncate(project.description, 100)}
  </p>
  <div style="display:flex; gap:8px; flex-wrap:wrap; font-size:11px;">
    ${langBadge}
    <span style="color:#6e7681;">⭐ ${project.stars}</span>
    <span style="color:#6e7681;">🍴 ${project.forks}</span>
    <span style="color:#6e7681;">🕐 ${project.lastUpdate}</span>
  </div>
</div>`;
}

/**
 * Genera la sección completa de proyectos en HTML
 */
function generateProjectsSection(projects: ProjectCard[]): string {
  if (projects.length === 0) {
    return `<p align="center"><em>🔍 No hay proyectos destacados aún. ¡Etiqueta tus repos con 'showcase'!</em></p>`;
  }

  const cards = projects.map(generateProjectCard).join('\n  ');
  const timestamp = new Date().toISOString();
  
  return `
<p align="center" style="margin:16px 0;">
  ${cards}
</p>
<p align="center">
  <sub>
    <img src="https://img.shields.io/badge/🔄_Last_Update-${encodeURIComponent(new Date().toLocaleDateString('es-ES'))}-blue?style=flat-square"/>
    <img src="https://img.shields.io/badge/Auto_Updated-GitHub_Actions-2ea44f?style=flat-square&logo=githubactions&logoColor=white"/>
  </sub>
</p>`;
}

// ─────────────────────────────────────────────────────────────
// 🌐 Lógica Principal de GitHub API
// ─────────────────────────────────────────────────────────────

/**
 * Obtiene repositorios del usuario filtrados por tags
 */
async function fetchFeaturedRepos(octokit: Octokit): Promise<ProjectCard[]> {
  console.log(`🔍 Fetching repos for @${CONFIG.username}...`);
  
  const { data: repos } = await octokit.repos.listForUser({
    username: CONFIG.username,
    per_page: 100,
    sort: CONFIG.sortBy,
    direction: 'desc',
  });

  // Filtrar y transformar
  const featured = repos
    .filter((repo: GitHubRepo) => 
      repo.visibility === 'public' &&
      !repo.fork &&
      repo.topics?.some(tag => CONFIG.targetTags.includes(tag.toLowerCase()))
    )
    .sort((a: GitHubRepo, b: GitHubRepo) => {
      if (CONFIG.sortBy === 'stars') return b.stargazers_count - a.stargazers_count;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    })
    .slice(0, CONFIG.maxProjects)
    .map((repo: GitHubRepo): ProjectCard => ({
      name: repo.name,
      description: repo.description || '',
      url: repo.html_url,
      stars: repo.stargazers_count,
      forks: repo.forks_count,
      language: repo.language || 'Unknown',
      lastUpdate: formatDateES(repo.updated_at),
    }));

  console.log(`✅ Found ${featured.length} featured projects`);
  return featured;
}

/**
 * Actualiza el README.md inyectando la sección de proyectos
 */
function updateReadmeFile(projectsSection: string): void {
  const readmePath = join(process.cwd(), CONFIG.readmePath);
  let content = readFileSync(readmePath, 'utf-8');
  
  const startMarker = '<!--START_PROJECTS_LIST-->';
  const endMarker = '<!--END_PROJECTS_LIST-->';
  
  const startIndex = content.indexOf(startMarker);
  const endIndex = content.indexOf(endMarker);
  
  if (startIndex === -1 || endIndex === -1) {
    throw new Error('❌ Marcadores no encontrados en README.md');
  }
  
  // Reconstruir contenido con nueva sección
  const newContent = 
    content.substring(0, startIndex + startMarker.length) + 
    '\n' + projectsSection + '\n' +
    content.substring(endIndex);
  
  writeFileSync(readmePath, newContent, 'utf-8');
  console.log(`💾 README.md actualizado exitosamente`);
}

// ─────────────────────────────────────────────────────────────
// 🚀 Punto de Entrada
// ─────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  try {
    console.log('🚀 Starting GitHub Profile Auto-Updater...');
    
    // Inicializar Octokit con o sin token (rate limit: 60/h sin token, 5000/h con token)
    const octokit = new Octokit({
      auth: CONFIG.token || undefined,
      userAgent: `${CONFIG.username}-profile-automation/1.0`,
    });
    
    // Fetch y procesar proyectos
    const projects = await fetchFeaturedRepos(octokit);
    const projectsSection = generateProjectsSection(projects);
    
    // Actualizar README
    updateReadmeFile(projectsSection);
    
    console.log('✨ Done! Profile README updated successfully.');
    
  } catch (error) {
    console.error('❌ Error:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

// Ejecutar si es el módulo principal
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { main, fetchFeaturedRepos, generateProjectsSection };