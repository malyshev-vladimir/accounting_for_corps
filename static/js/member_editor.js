export function markAsChanged(email) {
  const title = document.getElementById(`title-${email}`);
  const resident = document.getElementById(`residency-${email}`);
  const button = document.getElementById(`action-${email}`);

  if (!title || !resident || !button) return;

  const currentTitle = title.value;
  const originalTitle = title.dataset.original;

  const currentResident = resident.checked.toString();
  const originalResident = resident.dataset.original;

  const hasChanged =
    currentTitle !== originalTitle ||
    currentResident !== originalResident;

  if (hasChanged) {
    button.setAttribute('data-state', 'unsaved');
    button.classList.remove('text-primary');
    button.classList.add('text-success');
    button.innerHTML = '<i class="bi bi-save fs-6"></i>';
    button.title = 'Save changes';
  } else {
    button.setAttribute('data-state', 'saved');
    button.classList.remove('text-success');
    button.classList.add('text-primary');
    button.innerHTML = '<i class="bi bi-pencil-square fs-6"></i>';
    button.title = 'Edit';
  }
}

export function handleActionClick(email) {
  const titleEl = document.getElementById(`title-${email}`);
  const residentEl = document.getElementById(`residency-${email}`);
  const buttonEl = document.getElementById(`action-${email}`);

  const title = titleEl.value;
  const isResident = residentEl.checked;

  fetch('/admin/update_member_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, title, is_resident: isResident })
  })
    .then(res => {
      if (!res.ok) throw new Error("Failed to update");
      return res.json();
    })
    .then(() => {
      titleEl.dataset.original = title;
      residentEl.dataset.original = isResident.toString();

      markAsChanged(email); // сброс иконки
    })
    .catch(err => {
      alert("Fehler beim Speichern.");
      console.error(err);
    });
}

