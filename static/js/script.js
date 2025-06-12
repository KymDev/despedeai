// Exemplo simples para base.html ou index.html
document.addEventListener('DOMContentLoaded', () => {
    const categoriaSelect = document.getElementById('categoria');
    const modeloContainer = document.getElementById('modelo-container');

    categoriaSelect?.addEventListener('change', () => {
        modeloContainer.innerHTML = '<p>Carregando modelos...</p>';

        // Aqui você faria a requisição AJAX para atualizar os modelos
        // Exemplo usando fetch (supondo API /modelos/<categoria>)
        fetch(`/modelos/${categoriaSelect.value}`)
            .then(res => res.json())
            .then(data => {
                let html = '<select name="modelo" id="modelo">';
                data.modelos.forEach(m => {
                    html += `<option value="${m}">${m}</option>`;
                });
                html += '</select>';
                modeloContainer.innerHTML = html;
            })
            .catch(() => {
                modeloContainer.innerHTML = '<p>Erro ao carregar modelos.</p>';
            });
    });
});
