export function calculateSums() {
    const prices = window.beveragePrices || [];

    document.querySelectorAll("input.getr-value").forEach(input => {
        input.addEventListener("input", () => {
            const member = input.dataset.member;
            let sum = 0;

            document.querySelectorAll(`input[data-member='${member}']`).forEach(i => {
                const price = prices.find(p => p.name === i.dataset.bev)?.price || 0;
                const qty = parseInt(i.value) || 0;
                sum += price * qty;
            });

            const cell = document.getElementById(`sum-${member}`);
            if (cell) cell.textContent = sum.toFixed(2);
        });
    });
}
