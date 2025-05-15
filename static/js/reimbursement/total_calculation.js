export function update_total() {
    let total = 0;
    document.querySelectorAll(".expense-row.complete-entry").forEach(row => {
        total += parseFloat(row.querySelector(".amount-input").value) || 0;
    });
    document.getElementById("total").textContent = total.toFixed(2);
}