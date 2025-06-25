document.addEventListener('DOMContentLoaded', function () {
    let rowIndex = 1;

    window.addFineRow = function () {
        const tableBody = document.querySelector('#fines-table tbody');
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <select class="form-select" name="fines[${rowIndex}][email]" required>
                    <option value="" disabled selected>Mitglied wählen…</option>
                    ${membersOptions}
                </select>
            </td>
            <td style="width: 130px;">
                <input type="number" name="fines[${rowIndex}][amount]" class="form-control" step="0.01" required>
            </td>
            <td>
                <input type="text" name="fines[${rowIndex}][description]" class="form-control" required>
            </td>
            <td style="width: 50px;">
                <button type="button" class="btn btn-danger btn-sm remove-row"><i class="bi bi-x-lg"></i></button>
            </td>
        `;
        tableBody.appendChild(row);
        rowIndex++;
    };

    document.querySelector('#fines-table').addEventListener('click', function (event) {
        if (event.target.closest('.remove-row')) {
            event.target.closest('tr').remove();
        }
    });

    flatpickr(".flatpickr", {
        dateFormat: "d.m.Y"
    });
});
