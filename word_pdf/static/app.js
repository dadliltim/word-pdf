'use strict';
const $ = id => document.getElementById(id);
const fields = ['source', 'documents', 'pdf', 'reference'];
const token = document.querySelector('meta[name="app-token"]').content;
let current = null, selected = null, exported = null, busy = false;

function status(text, tone = '') {
  $('status-text').textContent = text;
  $('status').className = `status ${tone}`;
  $('status-symbol').textContent = tone === 'error' ? '!' : tone === 'success' ? '✓' : 'ℹ';
}

function updateControls() {
  document.querySelectorAll('button, input').forEach(element => { element.disabled = busy; });
  $('export-button').disabled = busy || selected === null || !current;
  $('previous').disabled = busy || !current || current.page === 0;
  $('next').disabled = busy || !current || (current.page + 1) * current.page_size >= current.total;
  $('spinner').hidden = !busy;
  document.querySelector('.results').setAttribute('aria-busy', String(busy));
  $('search-button').setAttribute('aria-busy', String(busy));
  $('clear').hidden = !$('reference').value;
}

function resetResults() {
  current = null; selected = null; exported = null;
  $('rows').replaceChildren();
  $('table-wrap').hidden = true;
  $('empty').hidden = false;
  $('empty-title').textContent = 'Votre recherche commence ici';
  $('empty-description').textContent = 'Les documents correspondant à votre référence apparaîtront dans cet espace.';
  $('count').textContent = 'En attente';
  $('range').textContent = 'Aucun document sélectionné';
  $('selection').textContent = 'Sélectionnez un document dans les résultats.';
  $('outputs').hidden = true;
  updateControls();
}

async function request(route, body, download = false) {
  let response;
  try {
    response = await fetch(`/api/${route}`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-App-Token': token}, body: JSON.stringify(body)});
  } catch {
    throw new Error(route === 'export'
      ? 'Connexion interrompue. La conversion a peut-être abouti : vérifiez les dossiers de sortie avant de réessayer.'
      : 'Le serveur ne répond pas. Vérifiez que la fenêtre Lancer-Web est ouverte, puis réessayez.');
  }
  if (!response.ok) {
    const result = await response.json();
    throw new Error(result.error || 'L’opération n’a pas pu être effectuée. Réessayez.');
  }
  return download ? response.blob() : response.json();
}

function render(result) {
  current = result; selected = null;
  $('rows').replaceChildren();
  $('empty').hidden = result.total > 0;
  $('table-wrap').hidden = result.total === 0;
  $('count').textContent = `${result.total.toLocaleString('fr-FR')} document${result.total === 1 ? '' : 's'}`;
  $('empty-title').textContent = 'Aucun document pour cette référence';
  $('empty-description').textContent = 'Vérifiez le numéro, l’année et le dossier source, puis relancez la recherche.';
  result.items.forEach(item => {
    const row = document.createElement('tr');
    const choice = document.createElement('td');
    const radio = document.createElement('input');
    radio.type = 'radio'; radio.name = 'document'; radio.id = `document-${item.index}`;
    radio.setAttribute('aria-label', `Sélectionner ${item.name}, dossier ${item.folder}`);
    radio.addEventListener('change', () => {
      selected = item.index;
      $('selection').textContent = `${result.reference}${item.extension} + ${result.reference}.pdf`;
      $('outputs').hidden = true; exported = null; updateControls();
    });
    choice.append(radio);
    const details = document.createElement('td');
    const label = document.createElement('label'); label.htmlFor = radio.id;
    label.append(document.createTextNode(item.name));
    const folder = document.createElement('span'); folder.className = 'subfolder'; folder.textContent = item.folder === '.' ? 'Dossier source' : item.folder;
    label.append(folder); details.append(label);
    const format = document.createElement('td');
    const tag = document.createElement('span'); tag.className = 'file-tag'; tag.textContent = item.extension.slice(1).toUpperCase();
    format.append(tag); row.append(choice, details, format); $('rows').append(row);
  });
  const start = result.page * result.page_size;
  $('range').textContent = result.total ? `${start + 1}–${Math.min(start + result.page_size, result.total)} sur ${result.total.toLocaleString('fr-FR')}` : '0 document';
  $('selection').textContent = 'Sélectionnez un document dans les résultats.';
  updateControls();
}

function extractReference(value) {
  const normalized = value.trim().replace(/^["'“”]+|["'“”]+$/g, '')
    .replace(/[٠-٩]/g, char => String(char.charCodeAt(0) - 0x660))
    .replace(/[۰-۹]/g, char => String(char.charCodeAt(0) - 0x6f0))
    .replace(/[０-９]/g, char => String(char.charCodeAt(0) - 0xff10))
    .replace(/\s*[-‐‑‒–—−－]\s*/g, '-');
  return normalized.match(/^([0-9]{1,12}-[0-9]{4})(?=$|[\s_.]|-(?![0-9]))/)?.[1] || null;
}

function validate() {
  let first = null;
  for (const key of fields) {
    const value = $(key).value.trim();
    let message = '';
    if (!value) message = key === 'reference' ? 'Saisissez une référence.' : 'Choisissez un dossier existant.';
    else if (key === 'reference') {
      const reference = extractReference(value);
      if (!reference) message = 'Saisissez une référence numéro-année ou un nom commençant par 0677-2026.';
      else $(key).value = reference;
    }
    $(`${key}-error`).textContent = message;
    $(key).setAttribute('aria-invalid', String(!!message));
    if (message && !first) first = $(key);
  }
  if (first) { first.focus(); status('Complétez les champs indiqués avant de rechercher.', 'error'); }
  return !first;
}

$('search-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || event.isComposing || !validate()) return;
  resetResults(); busy = true; updateControls();
  status('Recherche dans le dossier source et ses sous-dossiers…');
  try {
    const result = await request('search', Object.fromEntries(fields.map(key => [key, $(key).value.trim()])));
    render(result);
    status(result.total ? `${result.total} document(s) trouvé(s). Choisissez celui à convertir.` : 'Aucun document trouvé. Vérifiez la référence ou le dossier source.');
  } catch (error) { status(error.message, 'error'); }
  finally { busy = false; updateControls(); }
});

for (const key of fields) {
  $(key).addEventListener('input', () => {
    $(`${key}-error`).textContent = ''; $(key).setAttribute('aria-invalid', 'false');
    resetResults(); status('Paramètres modifiés. Lancez une recherche pour continuer.');
  });
}
$('reference').addEventListener('keydown', event => { if (event.isComposing && event.key === 'Enter') event.preventDefault(); });
$('clear').addEventListener('click', () => { $('reference').value = ''; $('reference').dispatchEvent(new Event('input')); $('reference').focus(); });

document.querySelectorAll('[data-folder]').forEach(button => button.addEventListener('click', async () => {
  if (busy) return;
  busy = true; updateControls(); status('Choisissez un dossier dans la fenêtre de sélection du PC.');
  try {
    const result = await request('browse', {});
    if (result.path) { $(button.dataset.folder).value = result.path; $(button.dataset.folder).dispatchEvent(new Event('input')); }
    else status('Sélection annulée. Les dossiers précédents sont conservés.');
  } catch (error) { status(error.message, 'error'); }
  finally { busy = false; updateControls(); button.focus(); }
}));

async function page(direction) {
  if (busy || !current) return;
  busy = true; updateControls(); status('Chargement des documents…');
  try { render(await request('page', {search_id: current.search_id, page: current.page + direction})); status('Sélectionnez le document à convertir.'); }
  catch (error) { status(error.message, 'error'); }
  finally { busy = false; updateControls(); }
}
$('previous').addEventListener('click', () => page(-1));
$('next').addEventListener('click', () => page(1));

$('export-button').addEventListener('click', async () => {
  if (busy || selected === null || !current) return;
  busy = true; updateControls(); status('Conversion en cours… Cette opération peut prendre jusqu’à deux minutes.');
  $('outputs').hidden = true;
  try {
    exported = await request('export', {search_id: current.search_id, index: selected});
    $('word-path').textContent = exported.word; $('pdf-path').textContent = exported.pdf;
    $('outputs').hidden = false;
    status('Export terminé. La copie Word et le PDF sont enregistrés dans leurs dossiers.', 'success');
  } catch (error) { status(error.message, 'error'); }
  finally { busy = false; updateControls(); }
});

for (const kind of ['word', 'pdf']) {
  $(`download-${kind}`).addEventListener('click', async () => {
    if (busy || !exported) return;
    busy = true; updateControls();
    try {
      const blob = await request('download', {export_id: exported.export_id, kind}, true);
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = exported[kind].split(/[\\/]/).pop();
      document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      status('Téléchargement demandé. Le fichier reste également dans son dossier de sortie.', 'success');
    } catch (error) { status(error.message, 'error'); }
    finally { busy = false; updateControls(); }
  });
}
window.addEventListener('beforeunload', event => { if (busy) { event.preventDefault(); event.returnValue = ''; } });
updateControls();
