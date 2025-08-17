

let currentCemetery = null;

document.addEventListener('DOMContentLoaded', function () {
    loadCemeteryCards();
});

function loadCemeteryCards() {
    const container = document.getElementById('cemetery-cards');
    container.innerHTML = '';

    fetch('/maskan/api/cemeteries/')
        .then(res => res.json())
        .then(data => {
            data.forEach(cem => {
                const card = document.createElement('div');
                card.className = 'col-md-6 col-lg-4 mb-4';
                card.innerHTML = `
                    <div class="card h-100 shadow-sm">
                        <img src="${cem.image || 'https://via.placeholder.com/400x300'}" class="card-img-top" alt="${cem.name}">
                        <div class="card-body">
                            <h5 class="card-title">${cem.name}</h5>
                            <p class="card-text">${cem.description || ''}</p>
                            <p class="text-muted"><i class="bi bi-geo-alt"></i> ${cem.location}</p>
                            <button class="btn btn-primary" onclick="loadGraveGrid(${cem.id}, '${cem.name}')">
                                View Graves
                            </button>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        })
        .catch(err => {
            container.innerHTML = '<p class="text-danger">Failed to load cemeteries.</p>';
        });
}

function loadGraveGrid(cemeteryId, cemeteryName) {
    currentCemetery = cemeteryId;
    document.getElementById('graves-title').textContent = `Graves in ${cemeteryName}`;
    document.getElementById('graves-section').style.display = 'block';

    const grid = document.getElementById('grave-grid');
    grid.innerHTML = '';

    fetch(`/maskan/api/cemeteries/${cemeteryId}/graves/`)
        .then(res => res.json())
        .then(data => {
            data.forEach(grave => {
                const slot = document.createElement('div');
                slot.className = `grave-slot ${grave.is_occupied ? 'occupied' : 'unoccupied'}`;
                slot.textContent = grave.row + grave.column;

                if (grave.is_occupied) {
                    slot.onclick = () => showGraveDetail(grave.id, grave.row + grave.column);
                }

                grid.appendChild(slot);
            });
        })
        .catch(err => {
            grid.innerHTML = '<p class="text-danger">Could not load graves.</p>';
        });
}

function showGraveDetail(graveId, label) {
    fetch(`/maskan/api/grave/${graveId}/`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert("No person found.");
                return;
            }

            const modal = new bootstrap.Modal(document.getElementById('graveModal'));
            const content = document.getElementById('modal-content');
            content.innerHTML = `
                <img src="${data.image || 'https://via.placeholder.com/150'}" class="rounded-circle mb-3" width="120" height="120">
                <h5 class="fw-bold">${data.name}</h5>
                <p><strong>Born:</strong> ${data.birth}</p>
                <p><strong>Died:</strong> ${data.death}</p>
                <p><strong>Grave:</strong> ${label}</p>
                <p class="text-muted">${data.description}</p>
            `;
            modal.show();
        })
        .catch(err => {
            alert("Error loading grave details.");
        });
}
