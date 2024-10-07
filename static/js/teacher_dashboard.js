// static/js/teacher_dashboard.js

// Function to fetch pending requests from the server
function fetchPendingRequests() {
    fetch('/api/pending_requests')
        .then(response => response.json())
        .then(data => {
            updateBorrowRequests(data.borrow_requests);
            updateDonationRequests(data.donation_requests);
        })
        .catch(error => console.error('Error fetching pending requests:', error));
}

// Function to update borrow requests table
function updateBorrowRequests(borrowRequests) {
    const borrowRequestsBody = document.getElementById('borrowRequestsBody');
    borrowRequestsBody.innerHTML = '';  // Clear the existing table

    borrowRequests.forEach(request => {
        const row = `
            <tr>
                <td>${request.book_title}</td>
                <td>${request.student_name}</td>
                <td>${request.class_name}</td>
                <td>${request.request_date}</td>
                <td>
                    <form action="/teacher/approve_borrow/${request.request_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-success btn-sm">Approve</button>
                    </form>
                    <form action="/teacher/reject_borrow/${request.request_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-danger btn-sm">Reject</button>
                    </form>
                </td>
            </tr>
        `;
        borrowRequestsBody.innerHTML += row;
    });
}

// Function to update donation requests table
function updateDonationRequests(donationRequests) {
    const donationRequestsBody = document.getElementById('donationRequestsBody');
    donationRequestsBody.innerHTML = '';  // Clear the existing table

    donationRequests.forEach(request => {
        const row = `
            <tr>
                <td>${request.book_title}</td>
                <td>${request.student_name}</td>
                <td>${request.class_name}</td>
                <td>${request.request_date}</td>
                <td>
                    <form action="/teacher/approve_donation/${request.request_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-success btn-sm">Approve</button>
                    </form>
                    <form action="/teacher/reject_donation/${request.request_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-danger btn-sm">Reject</button>
                    </form>
                </td>
            </tr>
        `;
        donationRequestsBody.innerHTML += row;
    });
}

// Poll the server every 10 seconds for new requests
setInterval(fetchPendingRequests, 10000);  // 10,000 ms = 10 seconds

// Initial fetch when the page loads
document.addEventListener('DOMContentLoaded', function () {
    fetchPendingRequests();
});
