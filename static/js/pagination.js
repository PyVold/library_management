// pagination.js

function paginateTable(tableId, paginationId, rowsPerPage) {
    const tableBody = document.getElementById(tableId);
    const rows = tableBody.getElementsByTagName('tr');
    const pagination = document.getElementById(paginationId);

    let currentPage = 1;
    const totalRows = rows.length;
    const totalPages = Math.ceil(totalRows / rowsPerPage);

    function showPage(page) {
        const start = (page - 1) * rowsPerPage;
        const end = start + rowsPerPage;

        // Hide all rows initially
        for (let i = 0; i < totalRows; i++) {
            rows[i].style.display = 'none';
        }

        // Display rows for the current page
        for (let i = start; i < end && i < totalRows; i++) {
            rows[i].style.display = '';
        }

        // Update pagination buttons
        updatePagination(page);
    }

    function updatePagination(current) {
        pagination.innerHTML = '';

        for (let page = 1; page <= totalPages; page++) {
            const pageButton = document.createElement('button');
            pageButton.innerText = page;
            pageButton.classList.add('page-btn');
            if (page === current) {
                pageButton.classList.add('active');
            }

            pageButton.addEventListener('click', function() {
                showPage(page);
            });

            pagination.appendChild(pageButton);
        }
    }

    // Initialize first page
    showPage(currentPage);
}

// Initialize pagination for borrow history and donation history
document.addEventListener('DOMContentLoaded', function() {
    paginateTable('borrowHistoryBody', 'borrowPagination', 5);
    paginateTable('donationHistoryBody', 'donationPagination', 5);
});
