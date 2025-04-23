function sendEmail(email) {
  fetch('/send_report', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email: email })
  })
  .then(response => {
    if (response.ok) {
      alert("Bericht wurde erfolgreich gesendet an " + email);
    } else {
      alert("Fehler beim Senden des Berichts an " + email);
    }
  })
  .catch(error => {
    console.error('Fehler beim Senden:', error);
    alert("Ein Fehler ist aufgetreten.");
  });
}
