const form = document.querySelector('#optimizer-form');
const message = document.querySelector('#form-message');
const scheduleBody = document.querySelector('#schedule-body');

function hours() {
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    demand_kwh: 1,
    solar_kwh: hour >= 8 && hour <= 16 ? 2 : 0,
    tariff_bdt_per_kwh: hour >= 18 && hour <= 21 ? 9 : 5,
  }));
}

function setText(id, value) { document.querySelector(`#${id}`).textContent = value; }

function renderResult(result) {
  setText('result-title', result.scenario_id);
  setText('total-grid', result.total_grid_kwh.toFixed(2));
  setText('total-cost', result.total_cost_bdt.toFixed(2));
  setText('peak-grid', result.peak_grid_kwh.toFixed(2));
  setText('schedule-count', `${result.hourly_plan.length} / 24 hours`);
  const directive = result.directive_interpretation[0];
  setText('directive-text', directive ? `${directive.directive_type.replaceAll('_', ' ')}: ${directive.explanation}` : 'No directive returned.');
  scheduleBody.innerHTML = result.hourly_plan.map((item) => `
    <tr>
      <td>${String(item.hour).padStart(2, '0')}:00</td>
      <td>${item.grid_kwh.toFixed(2)}</td>
      <td>${item.solar_used_kwh.toFixed(2)}</td>
      <td>${item.battery_energy_after_kwh.toFixed(2)}</td>
      <td class="action">${item.battery_action}</td>
    </tr>`).join('');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  message.textContent = 'Optimizing...';
  const payload = {
    scenario_id: document.querySelector('#scenario-id').value.trim(),
    operator_notes: [document.querySelector('#operator-note').value.trim()],
    hours: hours(),
    battery: {
      capacity_kwh: Number(document.querySelector('#capacity').value),
      initial_energy_kwh: Number(document.querySelector('#initial').value),
      minimum_energy_kwh: Number(document.querySelector('#minimum').value),
      max_charge_kwh_per_hour: Number(document.querySelector('#charge').value),
      max_discharge_kwh_per_hour: Number(document.querySelector('#charge').value),
    },
  };
  try {
    const response = await fetch('/optimize-energy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message || body.detail?.[0]?.msg || 'Request failed');
    renderResult(body);
    message.textContent = 'Schedule verified against the energy constraints.';
    message.style.color = '#147d63';
  } catch (error) {
    message.textContent = error.message;
    message.style.color = '#df6d4f';
  }
});
