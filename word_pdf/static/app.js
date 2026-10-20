'use strict';
const $ = id => document.getElementById(id);
const fields = ['source', 'documents', 'pdf', 'reference'];
const token = document.querySelector('meta[name="app-token"]').content;
let current = null, busy = false;
const selected = new Map();
const completed = new Set();

function status(text, tone = '') {
  $('status-text').textContent = text;
  $('status').className = `status ${tone}`;
  $('status-symbol').textContent = tone === 'error' ? '!' : tone === 'success' ? '✓' : 'ℹ';
}

function updateControls() {
  document.querySelectorAll('button, input, textarea').forEach(element => { element.disabled = busy; });
  $('use-proposal').disabled = busy || !$('proposed-searches').value.trim();
  document.querySelectorAll('#rows input').forEach(input => {
    input.disabled = busy || !current.items.find(item => item.index === Number(input.value))?.reference || completed.has(Number(input.value));
    input.checked = selected.has(Number(input.value));
  });
  $('export-button').disabled = busy || selected.size === 0 || !current;
  $('clear-selection').disabled = busy || selected.size === 0;
  const eligible = current?.items.filter(item => item.reference && !completed.has(item.index)) || [];
  const checked = eligible.filter(item => selected.has(item.index)).length;
  $('select-page').disabled = busy || !eligible.length;
  $('select-page').checked = eligible.length > 0 && checked === eligible.length;
  $('select-page').indeterminate = checked > 0 && checked < eligible.length;
  $('selection').textContent = selected.size ? `${selected.size} document(s) sélectionné(s), y compris sur les autres pages.` : 'Cochez un ou plusieurs documents dans les résultats.';
  $('selection-count').textContent = `${selected.size} sélectionné${selected.size > 1 ? 's' : ''}`;
  $('selection-count').classList.toggle('has-selection', selected.size > 0);
  $('previous').disabled = busy || !current || current.page === 0;
  $('next').disabled = busy || !current || (current.page + 1) * current.page_size >= current.total;
  $('spinner').hidden = !busy;
  document.querySelector('.results').setAttribute('aria-busy', String(busy));
  $('search-button').setAttribute('aria-busy', String(busy));
  $('clear').hidden = !$('reference').value;
}

function resetResults() {
  current = null; selected.clear(); completed.clear();
  $('rows').replaceChildren();
  $('table-wrap').hidden = true;
  $('empty').hidden = false;
  $('empty-title').textContent = 'Votre recherche commence ici';
  $('empty-description').textContent = 'Les documents Word correspondant à votre recherche apparaîtront ici.';
  $('count').textContent = 'En attente';
  $('range').textContent = 'Aucun document sélectionné';
  $('selection').textContent = 'Sélectionnez un document dans les résultats.';
  $('outputs').hidden = true;
  $('batch-progress').hidden = true;
  $('export-results').replaceChildren();
  $('missing-queries').hidden = true;
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

$('assistant-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || event.isComposing) return;
  const text = $('free-request').value.trim();
  $('assistant-error').textContent = '';
  $('assistant-proposal').hidden = true;
  $('proposed-searches').value = '';
  if (!text || text.length > 2000) {
    $('assistant-error').textContent = 'Décrivez votre recherche en 2 000 caractères maximum.';
    $('free-request').setAttribute('aria-invalid', 'true'); $('free-request').focus(); return;
  }
  $('free-request').setAttribute('aria-invalid', 'false');
  busy = true; updateControls(); status('Préparation locale des recherches…');
  try {
    const result = await request('prepare-search', {text});
    $('proposed-searches').value = result.queries.join(' ; ');
    $('assistant-warning').textContent = result.warnings.length ? result.warnings.join('\n') : 'Vérifiez les références et les noms avant de les utiliser.';
    $('assistant-proposal').hidden = false;
    status(result.queries.length ? 'Recherches proposées. Vérifiez-les avant de les utiliser.' : 'Précisez votre demande ou saisissez les recherches manuellement.');
  } catch (error) { $('assistant-error').textContent = error.message; status(error.message, 'error'); }
  finally { busy = false; updateControls(); }
});
$('free-request').addEventListener('input', () => {
  $('assistant-proposal').hidden = true; $('proposed-searches').value = '';
  $('assistant-error').textContent = ''; $('free-request').setAttribute('aria-invalid', 'false'); updateControls();
});
$('proposed-searches').addEventListener('input', updateControls);
$('use-proposal').addEventListener('click', () => {
  if (busy || !$('proposed-searches').value.trim()) return;
  $('reference').value = $('proposed-searches').value.trim();
  $('reference').dispatchEvent(new Event('input')); $('reference').focus();
  document.querySelector('.assistant').open = false;
  status('Recherches prêtes. Cliquez sur Rechercher pour consulter les documents.');
});

function render(result) {
  current = result;
  $('rows').replaceChildren();
  $('empty').hidden = result.total > 0;
  $('table-wrap').hidden = result.total === 0;
  $('count').textContent = `${result.total.toLocaleString('fr-FR')} document${result.total === 1 ? '' : 's'}`;
  $('empty-title').textContent = 'Aucun document pour cette recherche';
  $('empty-description').textContent = 'Essayez une autre partie du nom ou vérifiez le dossier source.';
  $('missing-queries').hidden = !result.missing_queries?.length;
  $('missing-queries').textContent = `Sans résultat : ${(result.missing_queries || []).join(' ; ')}`;
  result.items.forEach(item => {
    const row = document.createElement('tr');
    const choice = document.createElement('td');
    const radio = document.createElement('input');
    radio.type = 'checkbox'; radio.name = 'document'; radio.id = `document-${item.index}`; radio.value = item.index;
    radio.setAttribute('aria-label', `Sélectionner ${item.name}, dossier ${item.folder}`);
    radio.addEventListener('change', () => {
      if (radio.checked) selected.set(item.index, item); else selected.delete(item.index);
      status('Vérifiez les noms proposés, puis validez le traitement des documents cochés.');
      updateControls();
    });
    choice.append(radio);
    const details = document.createElement('td');
    const label = document.createElement('label'); label.htmlFor = radio.id;
    const filename = document.createElement('bdi'); filename.dir = 'auto'; filename.textContent = item.name;
    label.append(filename);
    const folder = document.createElement('span'); folder.className = 'subfolder'; folder.dir = 'auto'; folder.textContent = item.folder === '.' ? 'Dossier source' : item.folder;
    label.append(folder); details.append(label);
    const proposal = document.createElement('span'); proposal.className = 'subfolder'; proposal.dir = 'ltr';
    proposal.textContent = item.reference ? `Noms proposés : ${item.reference}${item.extension} et ${item.reference}.pdf` : item.reference_error || 'Référence numéro-année absente ou ambiguë : conversion indisponible';
    label.append(proposal);
    const format = document.createElement('td');
    const tag = document.createElement('span'); tag.className = 'file-tag'; tag.textContent = item.extension.slice(1).toUpperCase();
    format.append(tag); row.append(choice, details, format); $('rows').append(row);
  });
  const start = result.page * result.page_size;
  $('range').textContent = result.total ? `${start + 1}–${Math.min(start + result.page_size, result.total)} sur ${result.total.toLocaleString('fr-FR')}` : '0 document';
  $('selection').textContent = 'Sélectionnez un document dans les résultats.';
  updateControls();
}

function validate() {
  let first = null;
  for (const key of fields) {
    const value = $(key).value.trim();
    let message = '';
    if (!value) message = key === 'reference' ? 'Saisissez un nom, un mot ou une référence.' : 'Choisissez un dossier existant.';
    else if (key === 'reference' && value.length > 300) message = 'Limitez la recherche à 300 caractères.';
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
    status(result.total ? `${result.total} document(s) trouvé(s). Cochez ceux à convertir.` : 'Aucun document trouvé. Vérifiez la référence ou le dossier source.');
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
  try { render(await request('page', {search_id: current.search_id, page: current.page + direction})); status('Votre sélection est conservée entre les pages.'); }
  catch (error) { status(error.message, 'error'); }
  finally { busy = false; updateControls(); }
}
$('previous').addEventListener('click', () => page(-1));
$('next').addEventListener('click', () => page(1));

$('select-page').addEventListener('change', () => {
  for (const item of current?.items || []) {
    if (!item.reference || completed.has(item.index)) continue;
    if ($('select-page').checked) selected.set(item.index, item); else selected.delete(item.index);
  }
  updateControls();
});
$('clear-selection').addEventListener('click', () => { selected.clear(); updateControls(); });

async function download(exported, kind) {
  if (busy) return;
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
}

$('export-button').addEventListener('click', () => {
  if (busy || !selected.size || !current) return;
  const items = [...selected.values()], references = new Set();
  if (items.length > 100) { status('Traitez au maximum 100 documents à la fois. Réduisez la sélection.', 'error'); return; }
  for (const item of items) {
    if (references.has(item.reference)) {
      status(`Plusieurs documents produiraient ${item.reference}.pdf. Gardez un seul document pour cette référence.`, 'error');
      return;
    }
    references.add(item.reference);
  }
  $('batch-description').textContent = `${items.length} document(s) seront copiés et convertis dans les dossiers indiqués.`;
  $('batch-preview').replaceChildren();
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = `${item.name} → ${item.reference}${item.extension} + ${item.reference}.pdf`;
    $('batch-preview').append(li);
  }
  $('confirm-batch').textContent = `Traiter ${items.length} document(s)`;
  $('batch-dialog').showModal();
  $('cancel-batch').focus();
});
$('cancel-batch').addEventListener('click', () => $('batch-dialog').close());
$('batch-dialog').addEventListener('close', () => $('export-button').focus());
$('batch-dialog').addEventListener('keydown', event => {
  if (event.key !== 'Tab') return;
  const first = $('cancel-batch'), last = $('confirm-batch');
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});
$('confirm-batch').addEventListener('click', async () => {
  if (busy || !selected.size || !current) return;
  const items = [...selected.values()], searchId = current.search_id;
  $('batch-dialog').close();
  busy = true; updateControls();
  $('outputs').hidden = false; $('export-results').replaceChildren();
  $('batch-progress').hidden = false;
  $('export-progress').max = items.length; $('export-progress').value = 0;
  let succeeded = 0, failed = 0;
  for (const [position, item] of items.entries()) {
    status(`Traitement ${position + 1}/${items.length} : ${item.name}. Jusqu’à deux minutes par document.`);
    $('progress-label').textContent = `Document ${position + 1} sur ${items.length}`;
    const record = document.createElement('article'); record.className = 'batch-result';
    const heading = document.createElement('h4'); heading.textContent = item.name; record.append(heading);
    try {
      const exported = await request('export', {search_id: searchId, index: item.index});
      succeeded++; selected.delete(item.index); completed.add(item.index);
      for (const kind of ['word', 'pdf']) {
        const line = document.createElement('div'), path = document.createElement('p'); path.textContent = exported[kind];
        const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary';
        button.textContent = kind === 'pdf' ? 'Télécharger PDF' : 'Télécharger Word'; button.disabled = true;
        button.addEventListener('click', () => download(exported, kind));
        line.append(path, button); record.append(line);
      }
    } catch (error) {
      failed++;
      const message = document.createElement('p'); message.className = 'batch-error'; message.textContent = error.message; record.append(message);
    }
    $('export-results').append(record);
    $('batch-summary').textContent = `${succeeded} réussi(s) · ${failed} échec(s) · ${items.length - position - 1} restant(s)`;
    $('export-progress').value = position + 1;
  }
  status(`Traitement terminé : ${succeeded} réussi(s), ${failed} échec(s). Les documents en échec restent cochés.`, failed ? 'error' : 'success');
  $('progress-label').textContent = `Traitement terminé · ${items.length} document(s)`;
  busy = false; updateControls();
});
window.addEventListener('beforeunload', event => { if (busy) { event.preventDefault(); event.returnValue = ''; } });
updateControls();
