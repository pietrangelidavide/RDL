// Produce dist/artifact.html (pagina in un solo file: stile, caratteri e foto dentro, senza <html>/<head>/<body>,
// pronta da pubblicare come anteprima condivisibile) e dist/anteprima.html (stesso contenuto, si apre con doppio clic).
// Uso: node scripts/make-artifact.mjs
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const pub = join(root, 'public');
const dist = join(root, 'dist');
mkdirSync(dist, { recursive: true });
const uri = (file, type) => `data:${type};base64,${readFileSync(join(pub, file)).toString('base64')}`;

const css = readFileSync(join(pub, 'style.css'), 'utf8').replace(/url\('(fonts\/[^']+\.woff)'\)/g, (_, f) => `url('${uri(f, 'font/woff')}')`);
const page = readFileSync(join(pub, 'index.html'), 'utf8');
const title = /<title>([^<]+)<\/title>/.exec(page)[1];
const body = /<body>([\s\S]*)<\/body>/.exec(page)[1]
  .replace(/<img [^>]*>/, (img) => img.replace(/ srcset="[^"]*"/, '').replace(/ sizes="[^"]*"/, '').replace('src="foto.jpg"', `src="${uri('foto.jpg', 'image/jpeg')}"`));

const fragment = `<title>${title}</title>
<style>
${css}
</style>
${body}`;
writeFileSync(join(dist, 'artifact.html'), fragment);
writeFileSync(join(dist, 'anteprima.html'), `<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
</head>
<body>
${fragment}
</body>
</html>
`);
console.log(`dist/artifact.html: ${(fragment.length / 1024).toFixed(0)} KB`);
