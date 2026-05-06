document.addEventListener('DOMContentLoaded', function() {
    // Sidebar navigation
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (!href || !href.startsWith('#')) return;
            e.preventDefault();
            const targetId = href.substring(1);
            
            // Remove active classes
            document.querySelectorAll('.nav-link.active').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.dashboard-section.active').forEach(el => el.classList.remove('active'));
            
            // Add active classes
            this.classList.add('active');
            document.getElementById(targetId).classList.add('active');
            
        });
    });
    const modal = document.getElementById('editModal');
    const closeModal = document.querySelector('.close-modal');
    const editButtons = document.querySelectorAll('.edit-btn');
    const editForm = document.getElementById('editModelForm');
    
    // Open modal when edit button is clicked
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modelId = this.getAttribute('data-id');
            const modelName = this.getAttribute('data-name');
            
            document.getElementById('editModelId').value = modelId;
            document.getElementById('editModelName').value = modelName;
            modal.style.display = 'block';
            document.body.classList.add('modal-open'); // Add this line
            document.body.style.overflow = 'hidden'; // Disable scroll
            document.documentElement.style.overflow = 'hidden'; // Extra: lock html scroll
        });
    });
    
    // Close modal
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
        document.body.classList.remove('modal-open'); // Remove class
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }
    });
    
    // Handle form submission
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const modelId = formData.get('model_id');
        
        fetch(`/admin/edit_model/${modelId}`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Model updated successfully!');
                modal.style.display = 'none';
                // Get current tab from the active nav-link
                const activeTab = document.querySelector('.nav-link.active');
                let tab = 'segmentation';
                if (activeTab) {
                    const href = activeTab.getAttribute('href');
                    if (href.includes('classification')) tab = 'classification';
                    else if (href.includes('users')) tab = 'users';
                }
                // Reload with tab preserved
                location.href = `/admin/dashboard?tab=${tab}`;
            } else {
                alert(`Error: ${data.error || 'Failed to update model'}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating the model');
        });
    });

});