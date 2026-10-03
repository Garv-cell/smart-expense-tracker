const monthInput = document.getElementById('monthSelect');
const dateInput = document.getElementById('date');
const transactionForm = document.getElementById('transactionForm');
const budgetForm = document.getElementById('budgetForm');
const transactionTableBody = document.getElementById('transactionTableBody');
const searchInput = document.getElementById('searchInput');

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value || 0);

const setMessage = (elementId, text, type = 'success') => {
  const element = document.getElementById(elementId);
  element.textContent = text;
  element.className = `message ${type}`;
};

let categoryChart = null;
let trendChart = null;

const updateDateDefaults = () => {
  const defaultMonth = monthInput.value || new Date().toISOString().slice(0, 7);
  monthInput.value = defaultMonth;
  const today = new Date();
  if (!dateInput.value) {
    dateInput.value = today.toISOString().slice(0, 10);
  }
};

const fetchSummary = async () => {
  const month = monthInput.value || new Date().toISOString().slice(0, 7);
  const response = await fetch(`/api/summary?month=${month}`);
  const data = await response.json();

  document.getElementById('incomeTotal').textContent = formatCurrency(data.totals.income);
  document.getElementById('expenseTotal').textContent = formatCurrency(data.totals.expenses);
  document.getElementById('netTotal').textContent = formatCurrency(data.totals.net);

  if (data.budget_alerts && data.budget_alerts.length) {
    setMessage('budgetMessage', 'Budget alert: some categories are near or over target.', 'warning');
  }

  renderBudgetList(data.budgets, data.categories, data.budget_alerts);
  renderCharts(data.categories, data.monthly_trend);
};

const fetchTransactions = async () => {
  const month = monthInput.value || new Date().toISOString().slice(0, 7);
  const searchValue = searchInput.value.trim();
  const url = new URL('/api/transactions', window.location.origin);
  url.searchParams.set('month', month);
  if (searchValue) {
    url.searchParams.set('search', searchValue);
  }

  const response = await fetch(url);
  const transactions = await response.json();

  transactionTableBody.innerHTML = transactions
    .map(
      (item) => `
        <tr class="${item.type === 'income' ? 'income' : 'expense'}">
          <td>${item.date}</td>
          <td>${item.type}</td>
          <td>${item.category}</td>
          <td>${item.description || '—'}</td>
          <td>${item.type === 'income' ? '+' : '-'}${formatCurrency(item.amount)}</td>
        </tr>
      `
    )
    .join('') || '<tr><td colspan="5">No transactions found for this month.</td></tr>';
};

const renderBudgetList = (budgets, categoryTotals, budgetAlerts) => {
  const budgetMap = new Map((budgetAlerts || []).map((item) => [item.category, item]));
  const budgetList = document.getElementById('budgetList');

  const totalsMap = new Map((categoryTotals || []).map((item) => [item.category, item.total]));

  budgetList.innerHTML = (budgets || [])
    .map((item) => {
      const spent = totalsMap.get(item.category) || 0;
      const alert = budgetMap.get(item.category);
      const percent = item.amount ? Math.min((spent / item.amount) * 100, 100) : 0;
      return `
        <div class="budget-item">
          <div>
            <strong>${item.category}</strong>
            <span>${formatCurrency(spent)} / ${formatCurrency(item.amount)}</span>
          </div>
          <div>
            <span>${alert ? 'Near limit' : `${Math.round(percent)}%`}</span>
          </div>
        </div>
      `;
    })
    .join('') || '<p>No budgets set for this month.</p>';
};

const renderCharts = (categories, monthlyTrend) => {
  const categoryLabels = categories.map((item) => item.category);
  const categoryValues = categories.map((item) => item.total);

  if (categoryChart) {
    categoryChart.destroy();
  }

  categoryChart = new Chart(document.getElementById('categoryChart'), {
    type: 'bar',
    data: {
      labels: categoryLabels,
      datasets: [{
        label: 'Expense by Category',
        data: categoryValues,
        backgroundColor: ['#60a5fa', '#fca5a5', '#a7f3d0', '#fcd34d', '#c4b5fd', '#f9a8d4'],
        borderRadius: 8,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  if (trendChart) {
    trendChart.destroy();
  }

  trendChart = new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: {
      labels: (monthlyTrend || []).map((item) => item.label.split(' ')[0]),
      datasets: [
        {
          label: 'Income',
          data: (monthlyTrend || []).map((item) => item.income),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.15)',
          tension: 0.3,
        },
        {
          label: 'Expenses',
          data: (monthlyTrend || []).map((item) => item.expenses),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.12)',
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      scales: { y: { beginAtZero: true } },
    },
  });
};

const populateCategoryDatalist = async () => {
  const response = await fetch('/api/categories');
  const categories = await response.json();
  const datalist = document.getElementById('categoryOptions');
  datalist.innerHTML = categories
    .map((category) => `<option value="${category}"></option>`)
    .join('');
};

transactionForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    type: document.getElementById('type').value,
    category: document.getElementById('category').value,
    description: document.getElementById('description').value,
    amount: document.getElementById('amount').value,
    date: document.getElementById('date').value,
  };

  const response = await fetch('/api/transactions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (result.success) {
    setMessage('transactionMessage', result.message || 'Transaction added!', 'success');
    transactionForm.reset();
    updateDateDefaults();
    await fetchSummary();
    await fetchTransactions();
    await populateCategoryDatalist();
  } else {
    setMessage('transactionMessage', result.error || 'Unable to add transaction.', 'error');
  }
});

budgetForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    category: document.getElementById('budgetCategory').value,
    amount: document.getElementById('budgetAmount').value,
    month: monthInput.value,
  };

  const response = await fetch('/api/budgets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  if (result.success) {
    setMessage('budgetMessage', result.message || 'Budget saved!', 'success');
    budgetForm.reset();
    await fetchSummary();
    await populateCategoryDatalist();
  } else {
    setMessage('budgetMessage', result.error || 'Unable to save budget.', 'error');
  }
});

monthInput.addEventListener('change', async () => {
  updateDateDefaults();
  await fetchSummary();
  await fetchTransactions();
});

searchInput.addEventListener('input', fetchTransactions);

(async () => {
  const today = new Date();
  monthInput.value = today.toISOString().slice(0, 7);
  updateDateDefaults();
  await populateCategoryDatalist();
  await fetchSummary();
  await fetchTransactions();
})();
