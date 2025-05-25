document.addEventListener('DOMContentLoaded', function () {
    var cardDetailModalEl = document.getElementById('cardDetailModal');
    var cardModal = bootstrap.Modal.getInstance(cardDetailModalEl) || new bootstrap.Modal(cardDetailModalEl);
    var currentCardId = null; 
    var currentBoardId = null; 

    const boardContainer = document.getElementById('boardColumnsContainer');
    if (boardContainer && boardContainer.dataset.boardId) {
        currentBoardId = boardContainer.dataset.boardId;
    } else {
        const pathParts = window.location.pathname.split('/');
        if (pathParts.length >= 3 && pathParts[1] === 'boards') {
            const boardIdFromUrl = parseInt(pathParts[2], 10);
            if (!isNaN(boardIdFromUrl)) {
                currentBoardId = boardIdFromUrl;
            }
        }
    }


    var csrfTokenInput = document.querySelector('form input[name="csrf_token"]'); 
    var csrfToken = csrfTokenInput ? csrfTokenInput.value : null;
    if (!csrfToken) {
        console.error("CSRF Token not found on the page for AJAX!");
    }

    // Элементы для поиска и фильтрации
    const searchInput = document.getElementById('searchInput');
    const filterAssigneesList = document.getElementById('filterAssigneesList');
    const filterTagsList = document.getElementById('filterTagsList');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    
    let columnSortStates = {}; 


    if (cardDetailModalEl) {
        var modalForm = document.getElementById('editCardFormModal');
        var modalTitleField = document.getElementById('modalCardTitle');
        var modalDescriptionField = document.getElementById('modalCardDescription');
        var modalAssigneesSelect = document.getElementById('modalCardAssignees');
        var modalSelectedAssigneesPreview = document.getElementById('modalSelectedAssigneesPreview');
        var modalLabel = document.getElementById('cardDetailModalLabel');
        var deleteForm = document.getElementById('deleteCardFormModal');
        var saveButton = document.getElementById('saveCardModalBtn');

        var commentsListContainer = document.getElementById('commentsListContainer');
        var addCommentForm = document.getElementById('addCommentFormModal');
        var modalCommentText = document.getElementById('modalCommentText');
        var modalCommentTextError = document.getElementById('modalCommentTextError');
        var commentsLoader = document.getElementById('commentsLoader');
        
        var modalCardTagsSelect = document.getElementById('modalCardTags');
        var modalSelectedTagsPreview = document.getElementById('modalSelectedTagsPreview');
        
        var boardTagFormModal = document.getElementById('boardTagFormModal'); 
        var boardTagFormModalTitle = document.getElementById('boardTagFormModalTitle');
        var modalTagFormName = document.getElementById('modalTagFormName'); 
        var modalTagFormColor = document.getElementById('modalTagFormColor'); 
        var submitBoardTagBtn = document.getElementById('submitBoardTagBtn');
        var cancelEditBoardTagBtn = document.getElementById('cancelEditBoardTagBtn');

        var boardTagsListModal = document.getElementById('boardTagsListModal');
        var boardTagsLoaderModal = document.getElementById('boardTagsLoaderModal');


        function updateModalAssigneesPreview() {
            if (!modalAssigneesSelect || !modalSelectedAssigneesPreview) return;
            modalSelectedAssigneesPreview.innerHTML = '';
            const selectedOptions = Array.from(modalAssigneesSelect.selectedOptions);
            if (selectedOptions.length > 0) {
                 const titleEl = document.createElement('small');
                 titleEl.className = 'me-2 text-muted d-block w-100 mb-1';
                 titleEl.textContent = 'Выбранные исполнители:';
                 modalSelectedAssigneesPreview.appendChild(titleEl);
            }
            selectedOptions.forEach(option => {
                const assigneeName = option.text;
                let avatarUrl = option.dataset.avatarUrl || '/static/images/default_avatar.png';
                const img = document.createElement('img');
                img.src = avatarUrl;
                img.alt = assigneeName;
                img.title = assigneeName;
                img.className = 'rounded-circle me-1';
                img.style.width = '30px';
                img.style.height = '30px';
                img.style.objectFit = 'cover';
                modalSelectedAssigneesPreview.appendChild(img);
            });
        }
        if(modalAssigneesSelect) {
            modalAssigneesSelect.addEventListener('change', updateModalAssigneesPreview);
        }

        function renderSelectedTagsPreviewModal() {
            if (!modalCardTagsSelect || !modalSelectedTagsPreview) return;
            modalSelectedTagsPreview.innerHTML = '';
            const selectedOptions = Array.from(modalCardTagsSelect.selectedOptions);

            if (selectedOptions.length > 0) {
                const titleEl = document.createElement('small');
                titleEl.className = 'me-2 text-muted d-block w-100 mb-1';
                titleEl.textContent = 'Выбранные теги:';
                modalSelectedTagsPreview.appendChild(titleEl);
            }

            selectedOptions.forEach(option => {
                const tagName = option.text;
                const tagColor = option.dataset.color || '#808080';
                
                const tagPreviewEl = document.createElement('span');
                tagPreviewEl.className = 'tag-preview-item';
                tagPreviewEl.style.borderColor = tagColor; 
                
                const colorIndicator = document.createElement('span');
                colorIndicator.className = 'tag-color-preview';
                colorIndicator.style.backgroundColor = tagColor;
                
                const nameEl = document.createElement('span');
                nameEl.className = 'tag-name-preview';
                nameEl.textContent = tagName;
                
                tagPreviewEl.appendChild(colorIndicator);
                tagPreviewEl.appendChild(nameEl);
                modalSelectedTagsPreview.appendChild(tagPreviewEl);
            });
        }
        if (modalCardTagsSelect) {
            modalCardTagsSelect.addEventListener('change', renderSelectedTagsPreviewModal);
        }

        cardDetailModalEl.addEventListener('show.bs.modal', async function (event) {
            var cardElement = event.relatedTarget; 
            if (!cardElement || !cardElement.classList.contains('draggable-card')) {
                if (!currentCardId) {
                    console.error("Modal opened without a card context.");
                    return;
                }
            } else {
                 currentCardId = cardElement.getAttribute('data-card-id'); 
            }

            if (currentBoardId && currentCardId) {
                const newUrl = `/boards/${currentBoardId}/cards/${currentCardId}`;
                history.pushState({cardId: currentCardId}, `Карточка ${currentCardId}`, newUrl);
            }

            modalForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            modalForm.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
            
            resetBoardTagForm(); 

            if(modalCommentTextError) modalCommentTextError.textContent = '';
            if(modalCommentText) modalCommentText.classList.remove('is-invalid');

            try {
                const response = await fetch(`/cards/${currentCardId}/edit`, { headers: { 'X-Requested-With': 'XMLHttpRequest' }});
                if (!response.ok) throw new Error(`Failed to fetch card data: ${response.status}`);
                const data = await response.json();

                if (data.success && data.card) {
                    const cardData = data.card;
                    modalLabel.textContent = 'Карточка: ' + cardData.title;
                    modalTitleField.value = cardData.title;
                    modalDescriptionField.value = cardData.description;
                    modalForm.action = `/cards/${currentCardId}/edit`;
                    deleteForm.action = `/cards/${currentCardId}/delete`;

                    if (modalAssigneesSelect) {
                        Array.from(modalAssigneesSelect.options).forEach(option => {
                            option.selected = cardData.assignee_ids.includes(parseInt(option.value));
                            const assigneeData = cardData.assignees.find(a => a.id.toString() === option.value);
                            option.dataset.avatarUrl = assigneeData ? assigneeData.avatar_url : '/static/images/default_avatar.png';
                        });
                        updateModalAssigneesPreview();
                    }
                    
                    if (modalCardTagsSelect && data.board_tags) {
                        populateTagSelect(data.board_tags, cardData.tag_ids || []);
                    }

                } else {
                    throw new Error(data.error || "Card data not found");
                }
            } catch (error) {
                console.error("Error fetching card data for modal:", error);
                modalLabel.textContent = 'Ошибка загрузки карточки';
            }
            
            fetchBoardTags(currentBoardId);

            let deleteCsrfInput = deleteForm.querySelector('input[name="csrf_token"]');
            if (deleteCsrfInput && csrfToken) {
                 deleteCsrfInput.value = csrfToken;
            }
            
            fetchComments(currentCardId);
            if (addCommentForm) {
                addCommentForm.action = `/cards/${currentCardId}/comments/add`;
                let commentCsrf = addCommentForm.querySelector('input[name="csrf_token"]');
                if (!commentCsrf && csrfToken){
                    commentCsrf = document.createElement('input');
                    commentCsrf.type = 'hidden';
                    commentCsrf.name = 'csrf_token';
                    addCommentForm.appendChild(commentCsrf);
                }
                if (commentCsrf) commentCsrf.value = csrfToken;
            }
            if (boardTagFormModal) { 
                let tagCsrf = boardTagFormModal.querySelector('input[name="csrf_token"]');
                 if (!tagCsrf && csrfToken){
                    tagCsrf = document.createElement('input');
                    tagCsrf.type = 'hidden';
                    tagCsrf.name = 'csrf_token';
                    boardTagFormModal.appendChild(tagCsrf);
                }
                if(tagCsrf) tagCsrf.value = csrfToken;
            }
        });
        
        cardDetailModalEl.addEventListener('hidden.bs.modal', function () {
            if (commentsListContainer) commentsListContainer.innerHTML = ''; 
            if (addCommentForm) addCommentForm.reset(); 
            if (modalCommentText) modalCommentText.classList.remove('is-invalid');
            if (modalCommentTextError) modalCommentTextError.textContent = '';
            if (modalSelectedTagsPreview) modalSelectedTagsPreview.innerHTML = '';
            if (boardTagsListModal) boardTagsListModal.innerHTML = ''; 
            resetBoardTagForm();

            if (currentBoardId) {
                const boardUrl = `/boards/${currentBoardId}`;
                history.pushState({boardId: currentBoardId}, `Доска ${currentBoardId}`, boardUrl);
            }
        });

        saveButton.addEventListener('click', function() {
            let formCsrf = modalForm.querySelector('input[name="csrf_token"]');
            if (!formCsrf || !formCsrf.value) {
                 if(csrfToken){ 
                    if(!formCsrf){
                        formCsrf = document.createElement('input');
                        formCsrf.type = 'hidden';
                        formCsrf.name = 'csrf_token';
                        modalForm.appendChild(formCsrf);
                    }
                    formCsrf.value = csrfToken;
                 } else {
                    alert('Критическая ошибка: CSRF токен не найден для сохранения карточки. Обновите страницу.');
                    return;
                 }
            }

            fetch(modalForm.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: new FormData(modalForm)
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(({ status, body }) => {
                if (status === 200 && body.success) {
                    updateCardDisplay(body.card); 
                    applyFiltersAndSort(); 
                } else if (status === 400 && !body.success && body.errors) {
                    displayModalErrors(body.errors, modalForm);
                } else {
                    alert('Ошибка сохранения деталей карточки: ' + (body.error || body.message || 'Неизвестная ошибка сервера.'));
                }
            })
            .catch(error => {
                console.error('Error saving card details via modal:', error);
                alert('Произошла сетевая ошибка при сохранении деталей карточки.');
            });
        });
        
        deleteForm.addEventListener('submit', function(event) {
             event.preventDefault();
             let deleteCsrfTokenEl = deleteForm.querySelector('input[name="csrf_token"]');
             let deleteCsrfToken = deleteCsrfTokenEl ? deleteCsrfTokenEl.value : null;

             if (!deleteCsrfToken && csrfToken) { 
                 if (deleteCsrfTokenEl) {
                    deleteCsrfTokenEl.value = csrfToken;
                 } else { 
                    deleteCsrfTokenEl = document.createElement('input');
                    deleteCsrfTokenEl.type = 'hidden';
                    deleteCsrfTokenEl.name = 'csrf_token';
                    deleteCsrfTokenEl.value = csrfToken;
                    deleteForm.appendChild(deleteCsrfTokenEl);
                 }
                 deleteCsrfToken = csrfToken;
             }

             if (!deleteCsrfToken) {
                 alert('Ошибка: CSRF токен не найден для удаления. Обновите страницу.');
                 return;
             }
             if (!confirm('Удалить эту карточку? Все комментарии также будут удалены.')) return;

             fetch(deleteForm.action, {
                 method: 'POST',
                 headers: {
                     'X-Requested-With': 'XMLHttpRequest',
                     'X-CSRFToken': deleteCsrfToken 
                 }
             })
             .then(response => response.json().then(data => ({ status: response.status, body: data })))
             .then(({ status, body }) => {
                  if (status === 200 && body.success) {
                      cardModal.hide(); 
                      const cardIdToDelete = currentCardId; 
                      const cardElementToDelete = document.getElementById(`card-${cardIdToDelete}`);
                      if(cardElementToDelete) {
                          const columnList = cardElementToDelete.closest('.card-list');
                          cardElementToDelete.remove();
                          updateNoCardsPlaceholder(columnList); 
                      }
                  } else {
                      alert('Ошибка удаления карточки: ' + (body.error || body.message || 'Неизвестная ошибка.'));
                  }
             })
             .catch(error => {
                 console.error('Error deleting card via modal AJAX:', error);
                 alert('Произошла сетевая ошибка при удалении карточки.');
             });
        });

        function displayModalErrors(errors, targetForm) {
            targetForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            targetForm.querySelectorAll('.invalid-feedback').forEach(el => { el.textContent = ''; el.style.display = 'none';});
        
            for (const field in errors) {
                const inputElement = targetForm.querySelector(`[name="${field}"]`) || targetForm.querySelector(`#modal${field.charAt(0).toUpperCase() + field.slice(1)}`) || targetForm.querySelector(`#modalTagForm${field.charAt(0).toUpperCase() + field.slice(1)}`); 
                const errorElementId = `modal${field.charAt(0).toUpperCase() + field.slice(1)}Error` 
                                  || `modalTagForm${field.charAt(0).toUpperCase() + field.slice(1)}Error`; 
                let errorFeedbackElement = targetForm.querySelector(`.invalid-feedback[data-field-error="${field}"]`) || document.getElementById(errorElementId);
        
                if (inputElement) {
                    inputElement.classList.add('is-invalid');
                    if (!errorFeedbackElement) {
                        errorFeedbackElement = inputElement.closest('.mb-2, .mb-3').querySelector('.invalid-feedback'); 
                    }
                }
                if (errorFeedbackElement) {
                    errorFeedbackElement.textContent = errors[field];
                    errorFeedbackElement.style.display = 'block'; 
                } else {
                    console.warn(`No feedback element found for field "${field}" in form ${targetForm.id}`);
                }
            }
        }

        function updateTagsOnCardElement(cardElement, tags) {
            if (!cardElement) return;
            const tagsDisplayContainer = cardElement.querySelector('.card-tags-display');
            if (!tagsDisplayContainer) return;

            tagsDisplayContainer.innerHTML = ''; 
            if (tags && tags.length > 0) {
                tags.forEach(tag => {
                    const tagBadge = document.createElement('span');
                    tagBadge.className = 'tag-badge me-1';
                    tagBadge.style.backgroundColor = tag.color;
                    tagBadge.title = tag.name;
                    tagsDisplayContainer.appendChild(tagBadge);
                });
            }
        }

        function updateCardDisplay(cardData) {
            const cardElement = document.getElementById(`card-${cardData.id}`);
            if (!cardElement) return;

            cardElement.setAttribute('data-card-title', cardData.title);
            cardElement.setAttribute('data-card-description', cardData.description || '');
            cardElement.setAttribute('data-card-assignees', JSON.stringify(cardData.assignees || []));
            cardElement.setAttribute('data-card-tags', JSON.stringify(cardData.tags || [])); 

            let firstAssigneeName = '';
            if (cardData.assignees && cardData.assignees.length > 0) {
                firstAssigneeName = cardData.assignees[0].username.toLowerCase();
            }
            cardElement.setAttribute('data-first-assignee-name', firstAssigneeName);


            const titleDisplay = cardElement.querySelector('.card-title-display');
            if (titleDisplay) titleDisplay.textContent = cardData.title;
            if (currentCardId == cardData.id && modalLabel.textContent.startsWith('Карточка:')) {
                 modalLabel.textContent = 'Карточка: ' + cardData.title;
            }

            const descriptionIndicator = cardElement.querySelector('.card-description-indicator');
            const detailsContainer = cardElement.querySelector('.card-details-display');

            if (cardData.description) {
                if (descriptionIndicator) {
                    descriptionIndicator.style.display = 'inline';
                    descriptionIndicator.innerHTML = '<i class="bi bi-text-paragraph"></i>';
                } else if(detailsContainer) { 
                    const newIndicator = document.createElement('small');
                    newIndicator.className = 'text-muted card-description-indicator me-2';
                    newIndicator.title = 'Есть описание';
                    newIndicator.innerHTML = '<i class="bi bi-text-paragraph"></i>';
                    detailsContainer.prepend(newIndicator);
                }
            } else {
                 if (descriptionIndicator) descriptionIndicator.style.display = 'none';
            }

            const assigneesListDiv = cardElement.querySelector('.card-assignees-list');
            if (assigneesListDiv) {
                assigneesListDiv.innerHTML = ''; 
                if (cardData.assignees && cardData.assignees.length > 0) {
                    cardData.assignees.forEach(assignee => {
                        const img = document.createElement('img');
                        img.src = assignee.avatar_url;
                        img.alt = assignee.username;
                        img.title = assignee.username;
                        img.className = 'rounded-circle card-assignee-avatar';
                        img.style.width = '24px';
                        img.style.height = '24px';
                        img.style.objectFit = 'cover';
                        img.style.marginRight = '-8px';
                        img.style.border = '1px solid white';
                        assigneesListDiv.appendChild(img);
                    });
                } else {
                    const noAssigneePlaceholder = document.createElement('small');
                    noAssigneePlaceholder.className = 'text-muted fst-italic no-assignee-placeholder';
                    noAssigneePlaceholder.textContent = 'Нет исполнителей';
                    assigneesListDiv.appendChild(noAssigneePlaceholder);
                }
            }
            updateTagsOnCardElement(cardElement, cardData.tags); 
        }

        function fetchComments(cardIdToFetch) {
            if (!cardIdToFetch || !commentsListContainer) return;
            if (commentsLoader) commentsLoader.style.display = 'block';
            commentsListContainer.innerHTML = ''; 
            commentsListContainer.appendChild(commentsLoader);

            fetch(`/cards/${cardIdToFetch}/comments`)
                .then(response => response.json())
                .then(data => {
                    if (commentsLoader) commentsLoader.style.display = 'none';
                    if (data.success) {
                        renderComments(data.comments);
                    } else {
                        commentsListContainer.innerHTML = `<div class="list-group-item text-danger small">${data.error || 'Не удалось загрузить комментарии.'}</div>`;
                    }
                })
                .catch(error => {
                    if (commentsLoader) commentsLoader.style.display = 'none';
                    console.error('Error fetching comments:', error);
                    commentsListContainer.innerHTML = `<div class="list-group-item text-danger small">Ошибка сети при загрузке комментариев.</div>`;
                });
        }
        function renderComments(comments) {
            if (!commentsListContainer) return;
            commentsListContainer.innerHTML = ''; 
            if (comments.length === 0) {
                commentsListContainer.innerHTML = '<div class="list-group-item text-muted small fst-italic">Комментариев пока нет.</div>';
                return;
            }
            comments.forEach(comment => {
                const commentEl = createCommentElement(comment);
                commentsListContainer.appendChild(commentEl);
            });
            commentsListContainer.scrollTop = commentsListContainer.scrollHeight; 
        }
        function createCommentElement(comment) {
            const div = document.createElement('div');
            div.className = 'list-group-item comment-item py-2 px-3';
            div.id = `comment-${comment.id}`;
            div.dataset.commentId = comment.id;

            let actionsHtml = '';
            if (comment.can_edit || comment.can_delete) {
                actionsHtml = '<div class="comment-actions small mt-1">';
                if (comment.can_edit) {
                    actionsHtml += `<button class="btn btn-link btn-sm p-0 me-2 edit-comment-btn" data-comment-id="${comment.id}">Редактировать</button>`;
                }
                if (comment.can_delete) {
                    actionsHtml += `<button class="btn btn-link btn-sm p-0 text-danger delete-comment-btn" data-comment-id="${comment.id}">Удалить</button>`;
                }
                actionsHtml += '</div>';
            }

            div.innerHTML = `
                <div class="d-flex w-100">
                    <img src="${comment.author.avatar_url}" alt="${comment.author.username}" class="rounded-circle me-2" style="width:32px; height:32px; object-fit:cover;">
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="fw-bold">${escapeHtml(comment.author.username)}</small>
                            <small class="text-muted">${comment.timestamp}</small>
                        </div>
                        <p class="mb-1 comment-text">${escapeHtml(comment.text)}</p>
                        ${actionsHtml}
                    </div>
                </div>
                <div class="edit-comment-form-container" style="display:none;"></div>
            `;
            return div;
        }
        if (addCommentForm) {
            addCommentForm.addEventListener('submit', function(event) {
                event.preventDefault();
                if (!currentCardId || !csrfToken) {
                    alert("Ошибка: Не удалось определить карточку или CSRF токен.");
                    return;
                }
                
                const formData = new FormData(addCommentForm);
                if (!formData.has('csrf_token') && csrfToken) {
                    formData.append('csrf_token', csrfToken);
                }

                fetch(addCommentForm.action, {
                    method: 'POST',
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    body: formData
                })
                .then(response => response.json().then(data => ({status: response.status, body: data})))
                .then(({status, body}) => {
                    if (modalCommentText) modalCommentText.classList.remove('is-invalid');
                    if (modalCommentTextError) modalCommentTextError.textContent = '';

                    if (status === 201 && body.success) {
                        const newCommentEl = createCommentElement(body.comment);
                        const noCommentsPlaceholder = commentsListContainer.querySelector('.fst-italic');
                        if (noCommentsPlaceholder && noCommentsPlaceholder.textContent.includes("Комментариев пока нет")) {
                            noCommentsPlaceholder.remove();
                        }
                        commentsListContainer.appendChild(newCommentEl);
                        addCommentForm.reset();
                        commentsListContainer.scrollTop = commentsListContainer.scrollHeight;
                    } else if (status === 400 && !body.success && body.errors) {
                        if (body.errors.text && modalCommentText && modalCommentTextError) {
                            modalCommentText.classList.add('is-invalid');
                            modalCommentTextError.textContent = body.errors.text;
                        } else { 
                             alert("Ошибка валидации: " + JSON.stringify(body.errors));
                        }
                    } else {
                        alert('Ошибка добавления комментария: ' + (body.error || body.message || "Неизвестная ошибка"));
                    }
                })
                .catch(error => {
                    console.error("Error adding comment:", error);
                    alert("Сетевая ошибка при добавлении комментария.");
                });
            });
        }
        if (commentsListContainer) {
            commentsListContainer.addEventListener('click', function(event) {
                const target = event.target;
                
                if (target.classList.contains('edit-comment-btn')) {
                    const commentId = target.dataset.commentId;
                    handleEditCommentClick(commentId);
                } else if (target.classList.contains('delete-comment-btn')) {
                    const commentId = target.dataset.commentId;
                    handleDeleteCommentClick(commentId);
                } else if (target.classList.contains('save-edited-comment-btn')) {
                    const formElement = target.closest('.edit-comment-form');
                    const commentId = formElement ? formElement.dataset.commentId : null;
                    if (commentId && formElement) { 
                        handleSaveEditedComment(commentId, formElement);
                    }
                } else if (target.classList.contains('cancel-edit-comment-btn')) {
                     const formElement = target.closest('.edit-comment-form');
                     const commentId = formElement ? formElement.dataset.commentId : null;
                     if (commentId) { 
                        hideEditCommentForm(commentId);
                     }
                }
            });
        }
        function handleEditCommentClick(commentId) {
            const commentItem = document.getElementById(`comment-${commentId}`);
            if (!commentItem) return;

            document.querySelectorAll('.edit-comment-form-container').forEach(container => {
                const otherCommentId = container.closest('.comment-item')?.dataset.commentId;
                if (otherCommentId && otherCommentId !== commentId) { 
                    hideEditCommentForm(otherCommentId);
                }
            });

            const commentTextEl = commentItem.querySelector('.comment-text');
            const currentText = commentTextEl.textContent; 
            const formContainer = commentItem.querySelector('.edit-comment-form-container');
            
            commentTextEl.style.display = 'none';
            const actionsDiv = commentItem.querySelector('.comment-actions');
            if(actionsDiv) actionsDiv.style.display = 'none';

            const csrfForEdit = csrfToken || ''; 

            formContainer.innerHTML = `
                <form class="edit-comment-form mt-2" data-comment-id="${commentId}">
                    <input type="hidden" name="csrf_token" value="${csrfForEdit}">
                    <textarea name="text" class="form-control form-control-sm mb-2" rows="3" required>${escapeHtml(currentText)}</textarea>
                    <div class="invalid-feedback" data-field-error="text"></div>
                    <button type="button" class="btn btn-sm btn-primary save-edited-comment-btn">Сохранить</button>
                    <button type="button" class="btn btn-sm btn-secondary ms-1 cancel-edit-comment-btn">Отмена</button>
                </form>
            `;
            formContainer.style.display = 'block';
            formContainer.querySelector('textarea').focus();
        }
        function hideEditCommentForm(commentId) {
            const commentItem = document.getElementById(`comment-${commentId}`);
            if (!commentItem) return;
            const commentTextEl = commentItem.querySelector('.comment-text');
            const formContainer = commentItem.querySelector('.edit-comment-form-container');
            const actionsDiv = commentItem.querySelector('.comment-actions');

            if (formContainer) { 
                formContainer.style.display = 'none';
                formContainer.innerHTML = '';
            }
            if (commentTextEl) commentTextEl.style.display = 'block'; 
            if(actionsDiv) actionsDiv.style.display = 'block'; 
        }
        function handleSaveEditedComment(commentId, formElement) {
            if(!formElement || !commentId) { return; }
            const formData = new FormData(formElement);
            if (!formData.has('csrf_token') && csrfToken) { formData.append('csrf_token', csrfToken); }

            fetch(`/comments/${commentId}/edit`, {
                method: 'POST',
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                body: formData
            })
            .then(response => { 
                if (!response.ok) { return response.text().then(text => { throw new Error(`Server responded with ${response.status}: ${text}`); }); }
                return response.json(); 
            })
            .then(body => { 
                const textarea = formElement.querySelector('textarea[name="text"]');
                const errorDiv = formElement.querySelector('.invalid-feedback[data-field-error="text"]');
                if (textarea) textarea.classList.remove('is-invalid');
                if (errorDiv) errorDiv.textContent = '';

                if (body.success) { 
                    const commentItem = document.getElementById(`comment-${commentId}`);
                    const commentTextEl = commentItem.querySelector('.comment-text');
                    commentTextEl.textContent = body.comment.text; 
                    hideEditCommentForm(commentId);
                } else if (!body.success && body.errors) { 
                     if (body.errors.text && textarea && errorDiv) {
                        textarea.classList.add('is-invalid');
                        errorDiv.textContent = body.errors.text;
                    } else { alert("Ошибка валидации: " + JSON.stringify(body.errors)); }
                } else { alert('Ошибка редактирования комментария: ' + (body.error || body.message || "Неизвестная ошибка")); }
            })
            .catch(error => {
                console.error("Error editing comment:", error);
                alert("Ошибка при редактировании комментария. " + error.message);
            });
        }
        function handleDeleteCommentClick(commentId) {
            if (!confirm("Удалить этот комментарий?")) return;
            if (!csrfToken) { alert("Ошибка: CSRF токен не найден."); return; }

            fetch(`/comments/${commentId}/delete`, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrfToken }
            })
            .then(response => response.json().then(data => ({status: response.status, body: data})))
            .then(({status, body}) => {
                if (status === 200 && body.success) {
                    const commentItem = document.getElementById(`comment-${commentId}`);
                    if (commentItem) commentItem.remove();
                    if (commentsListContainer.children.length === 0) {
                         commentsListContainer.innerHTML = '<div class="list-group-item text-muted small fst-italic">Комментариев пока нет.</div>';
                    }
                } else {
                    alert('Ошибка удаления комментария: ' + (body.error || body.message || "Неизвестная ошибка"));
                }
            })
            .catch(error => {
                console.error("Error deleting comment:", error);
                alert("Сетевая ошибка при удалении комментария.");
            });
        }
        function escapeHtml(unsafe) {
            if (unsafe === null || typeof unsafe === 'undefined') return '';
            return unsafe.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }
        
        async function fetchBoardTags(boardId, selectTagIdToEdit = null) {
            if (!boardId || !boardTagsListModal || !boardTagsLoaderModal) return;
            boardTagsLoaderModal.style.display = 'block';
            boardTagsListModal.innerHTML = '';

            try {
                const response = await fetch(`/api/boards/${boardId}/tags`);
                if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
                const data = await response.json();
                boardTagsLoaderModal.style.display = 'none';
                if (data.success) {
                    renderBoardTagsList(data.tags);
                    if (selectTagIdToEdit) { 
                        const tagToEditEl = boardTagsListModal.querySelector(`.list-group-item[data-tag-id="${selectTagIdToEdit}"]`);
                    }
                } else {
                    boardTagsListModal.innerHTML = `<div class="list-group-item text-danger small">${data.error || 'Не удалось загрузить теги доски.'}</div>`;
                }
            } catch (error) {
                boardTagsLoaderModal.style.display = 'none';
                console.error('Error fetching board tags:', error);
                boardTagsListModal.innerHTML = `<div class="list-group-item text-danger small">Ошибка сети при загрузке тегов доски.</div>`;
            }
        }

        function renderBoardTagsList(tags) {
            if (!boardTagsListModal) return;
            boardTagsListModal.innerHTML = '';
            if (tags.length === 0) {
                boardTagsListModal.innerHTML = '<div class="list-group-item text-muted small fst-italic">Тегов на доске пока нет.</div>';
                return;
            }
            tags.forEach(tag => {
                const item = document.createElement('div');
                item.className = 'list-group-item d-flex justify-content-between align-items-center py-1 px-2'; 
                item.dataset.tagId = tag.id;
                item.dataset.tagName = tag.name;
                item.dataset.tagColor = tag.color;
                
                const tagInfo = document.createElement('span');
                tagInfo.className = 'd-flex align-items-center';
                const colorPreview = document.createElement('span');
                colorPreview.className = 'tag-color-preview me-2';
                colorPreview.style.backgroundColor = tag.color;
                tagInfo.appendChild(colorPreview);
                tagInfo.append(escapeHtml(tag.name));
                
                const actions = document.createElement('div');
                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-link btn-sm p-0 me-2 btn-edit-board-tag'; 
                editBtn.innerHTML = '✏️'; 
                editBtn.title = "Редактировать тег";
                editBtn.dataset.tagId = tag.id;
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-link btn-sm p-0 text-danger btn-delete-board-tag'; 
                deleteBtn.innerHTML = '✖';  
                deleteBtn.title = "Удалить тег";
                deleteBtn.dataset.tagId = tag.id;

                actions.appendChild(editBtn); 
                actions.appendChild(deleteBtn);

                item.appendChild(tagInfo);
                item.appendChild(actions);
                boardTagsListModal.appendChild(item);
            });
        }

        function populateTagSelect(allBoardTags, selectedCardTagIds = []) {
            if (!modalCardTagsSelect) return;
            const currentSelections = Array.from(modalCardTagsSelect.selectedOptions).map(opt => opt.value); 
            modalCardTagsSelect.innerHTML = ''; 
        
            allBoardTags.forEach(tag => {
                const option = document.createElement('option');
                option.value = tag.id;
                option.textContent = tag.name;
                option.dataset.color = tag.color; 
                if (selectedCardTagIds.includes(tag.id) || currentSelections.includes(tag.id.toString())) { 
                    option.selected = true;
                }
                modalCardTagsSelect.appendChild(option);
            });
            renderSelectedTagsPreviewModal(); 
        }

        function resetBoardTagForm() {
            if (!boardTagFormModal) return;
            boardTagFormModal.reset();
            boardTagFormModal.dataset.currentTagId = ''; 
            if (boardTagFormModalTitle) boardTagFormModalTitle.textContent = 'Создать новый тег';
            if (submitBoardTagBtn) submitBoardTagBtn.textContent = 'Создать тег';
            if (cancelEditBoardTagBtn) cancelEditBoardTagBtn.style.display = 'none';
            boardTagFormModal.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            boardTagFormModal.querySelectorAll('.invalid-feedback').forEach(el => {el.textContent = ''; el.style.display = 'none';});
        }
        if(cancelEditBoardTagBtn) {
            cancelEditBoardTagBtn.addEventListener('click', resetBoardTagForm);
        }

        if (boardTagFormModal) { 
            boardTagFormModal.addEventListener('submit', async function(event) {
                event.preventDefault();
                if (!currentBoardId || !csrfToken) {
                    alert("Ошибка: Не удалось определить доску или CSRF токен для операции с тегом.");
                    return;
                }
                
                const formData = new FormData(boardTagFormModal);
                if (!formData.has('csrf_token') && csrfToken) {
                    formData.append('csrf_token', csrfToken);
                }

                const tagIdToEdit = boardTagFormModal.dataset.currentTagId;
                const url = tagIdToEdit ? `/api/tags/${tagIdToEdit}/edit` : `/api/boards/${currentBoardId}/tags/create`;
                const method = 'POST'; 

                try {
                    const response = await fetch(url, {
                        method: method,
                        headers: {'X-Requested-With': 'XMLHttpRequest'},
                        body: formData
                    });
                    const bodyData = await response.json(); 
                    const status = response.status;
                
                    boardTagFormModal.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
                    boardTagFormModal.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');

                    if ((status === 201 || status === 200) && bodyData.success && bodyData.tag) {
                        resetBoardTagForm(); 
                        await fetchBoardTags(currentBoardId); 
                        
                        const boardTagsResponse = await fetch(`/api/boards/${currentBoardId}/tags`);
                        const allBoardTagsData = await boardTagsResponse.json(); 
                        if (allBoardTagsData.success) { 
                            const currentSelectedCardTagIds = Array.from(modalCardTagsSelect.selectedOptions).map(opt => parseInt(opt.value));
                            if (status === 201 && !currentSelectedCardTagIds.includes(bodyData.tag.id)) {
                                currentSelectedCardTagIds.push(bodyData.tag.id);
                            }
                            populateTagSelect(allBoardTagsData.tags, currentSelectedCardTagIds); 
                        }
                        updateAllCardTagDisplays(bodyData.tag.id, bodyData.tag, (status === 200 && tagIdToEdit)); 
                        applyFiltersAndSort(); 
                        
                    } else if (status === 400 && !bodyData.success && bodyData.errors) {
                        displayModalErrors(bodyData.errors, boardTagFormModal);
                    } else {
                        alert(`Ошибка ${tagIdToEdit ? 'редактирования' : 'создания'} тега: ` + (bodyData.error || bodyData.message || "Неизвестная ошибка"));
                    }
                } catch (error) {
                    console.error(`Error ${tagIdToEdit ? 'editing' : 'creating'} tag:`, error);
                    alert(`Сетевая ошибка при ${tagIdToEdit ? 'редактировании' : 'создании'} тега.`);
                }
            });
        }
        
        if (boardTagsListModal) {
            boardTagsListModal.addEventListener('click', async function(event){
                const target = event.target;
                const editButton = target.closest('.btn-edit-board-tag');
                const deleteButton = target.closest('.btn-delete-board-tag');

                if (editButton) {
                    const tagItem = editButton.closest('.list-group-item');
                    const tagId = tagItem.dataset.tagId;
                    const tagName = tagItem.dataset.tagName;
                    const tagColor = tagItem.dataset.tagColor;

                    if (boardTagFormModalTitle) boardTagFormModalTitle.textContent = `Редактировать тег: ${escapeHtml(tagName)}`;
                    if (modalTagFormName) modalTagFormName.value = tagName;
                    if (modalTagFormColor) modalTagFormColor.value = tagColor;
                    if (submitBoardTagBtn) submitBoardTagBtn.textContent = 'Сохранить изменения';
                    if (boardTagFormModal) boardTagFormModal.dataset.currentTagId = tagId;
                    if (cancelEditBoardTagBtn) cancelEditBoardTagBtn.style.display = 'inline-block';
                    
                    boardTagFormModal.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
                    boardTagFormModal.querySelectorAll('.invalid-feedback').forEach(el => { el.textContent = ''; el.style.display = 'none'; });
                }

                if (deleteButton) {
                    const tagItem = deleteButton.closest('.list-group-item');
                    const tagId = tagItem.dataset.tagId;
                    const tagName = tagItem.dataset.tagName;

                    if (!confirm(`Удалить тег "${escapeHtml(tagName)}"? Он будет удален со всех карточек.`)) return;
                    if (!csrfToken) { alert("Ошибка: CSRF токен."); return; }

                    try {
                        const response = await fetch(`/api/tags/${tagId}/delete`, {
                            method: 'POST',
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            }
                        });
                        const body = await response.json();
                        if (response.ok && body.success) {
                            await fetchBoardTags(currentBoardId); 
                           
                            const boardTagsResponse = await fetch(`/api/boards/${currentBoardId}/tags`);
                            const allBoardTagsData = await boardTagsResponse.json(); 
                            if (allBoardTagsData.success) { 
                                const currentSelectedCardTagIds = Array.from(modalCardTagsSelect.selectedOptions)
                                                                     .map(opt => parseInt(opt.value))
                                                                     .filter(id => id !== parseInt(tagId)); 
                                populateTagSelect(allBoardTagsData.tags, currentSelectedCardTagIds); 
                            }
                            updateAllCardTagDisplays(tagId, null, false, true); 
                            applyFiltersAndSort(); 
                        } else {
                            alert('Ошибка удаления тега: ' + (body.error || body.message || "Неизвестная ошибка."));
                        }
                    } catch (error) {
                        console.error("Error deleting board tag:", error);
                        alert("Сетевая ошибка при удалении тега.");
                    }
                }
            });
        }

        function updateAllCardTagDisplays(tagId, updatedTagData, isEdit = false, isDeletion = false) {
            document.querySelectorAll('.draggable-card').forEach(cardEl => {
                let cardTagsJson = cardEl.getAttribute('data-card-tags');
                if (!cardTagsJson) return;

                try {
                    let cardTags = JSON.parse(cardTagsJson);
                    let changed = false;

                    if (isDeletion) {
                        const initialLength = cardTags.length;
                        cardTags = cardTags.filter(t => t.id !== parseInt(tagId));
                        if (cardTags.length !== initialLength) changed = true;
                    } else if (isEdit && updatedTagData) { 
                        const tagIndex = cardTags.findIndex(t => t.id === parseInt(tagId));
                        if (tagIndex > -1) {
                            cardTags[tagIndex].name = updatedTagData.name;
                            cardTags[tagIndex].color = updatedTagData.color;
                            changed = true;
                        }
                    }
                    if (changed) {
                        cardEl.setAttribute('data-card-tags', JSON.stringify(cardTags));
                        updateTagsOnCardElement(cardEl, cardTags);
                    }
                } catch (e) {
                    console.error("Error parsing or updating card tags on element:", e);
                }
            });
        }

        function checkUrlAndOpenModal() {
            const path = window.location.pathname;
            const match = path.match(/\/boards\/(\d+)\/cards\/(\d+)/);
            if (match) {
                const boardIdFromUrl = match[1];
                const urlCardId = match[2]; 
                if (boardIdFromUrl && urlCardId) {
                    if (!currentBoardId) currentBoardId = parseInt(boardIdFromUrl, 10);
                    currentCardId = urlCardId; 

                    const cardElement = document.getElementById(`card-${urlCardId}`);
                    if (cardElement) {
                        cardModal.show(cardElement); 
                    } else {
                        cardModal.show(); 
                    }
                }
            }
        }
        checkUrlAndOpenModal();
        window.addEventListener('popstate', function (event) {
            const path = window.location.pathname;
            const match = path.match(/\/boards\/(\d+)\/cards\/(\d+)/);
            if (match) {
                checkUrlAndOpenModal();
            } else {
                if (cardDetailModalEl.classList.contains('show')) {
                    cardModal.hide();
                }
            }
        });
    } 

    // --- Логика Поиска, Фильтрации и Сортировки ---
    function applyFiltersAndSort() {
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        
        const selectedAssigneeIds = [];
        if (filterAssigneesList) {
            filterAssigneesList.querySelectorAll('.filter-checkbox:checked').forEach(cb => {
                selectedAssigneeIds.push(cb.value);
            });
        }

        const selectedTagIds = [];
        if (filterTagsList) {
            filterTagsList.querySelectorAll('.filter-checkbox:checked').forEach(cb => {
                selectedTagIds.push(cb.value);
            });
        }

        document.querySelectorAll('.card-list').forEach(columnList => {
            const columnId = columnList.dataset.columnId;
            let visibleCardsInColumn = [];

            columnList.querySelectorAll('.draggable-card').forEach(cardEl => {
                const cardTitle = (cardEl.dataset.cardTitle || '').toLowerCase();
                const cardDescription = (cardEl.dataset.cardDescription || '').toLowerCase();
                
                let cardAssignees = [];
                try { cardAssignees = JSON.parse(cardEl.dataset.cardAssignees || '[]').map(a => a.id.toString()); } 
                catch (e) { console.warn('Error parsing card assignees for filter:', e, cardEl.dataset.cardAssignees); }

                let cardTags = [];
                try { cardTags = JSON.parse(cardEl.dataset.cardTags || '[]').map(t => t.id.toString()); }
                catch (e) { console.warn('Error parsing card tags for filter:', e, cardEl.dataset.cardTags); }

                const searchMatch = searchTerm === '' || cardTitle.includes(searchTerm) || cardDescription.includes(searchTerm);

                let assigneeMatch = true;
                if (selectedAssigneeIds.length > 0) {
                    assigneeMatch = selectedAssigneeIds.some(id => cardAssignees.includes(id));
                }

                let tagMatch = true;
                if (selectedTagIds.length > 0) {
                    tagMatch = selectedTagIds.some(id => cardTags.includes(id));
                }

                if (searchMatch && assigneeMatch && tagMatch) {
                    cardEl.style.display = '';
                    visibleCardsInColumn.push(cardEl);
                } else {
                    cardEl.style.display = 'none';
                }
            });

            const sortOrder = columnSortStates[columnId] || 'none'; 
            if (sortOrder !== 'none' && visibleCardsInColumn.length > 0) {
                visibleCardsInColumn.sort((a, b) => {
                    const nameA = a.dataset.firstAssigneeName || '\uffff'; 
                    const nameB = b.dataset.firstAssigneeName || '\uffff';
                    
                    if (sortOrder === 'asc') {
                        return nameA.localeCompare(nameB);
                    } else { 
                        return nameB.localeCompare(nameA);
                    }
                });
            }
            
            visibleCardsInColumn.forEach(cardNode => columnList.appendChild(cardNode));
            updateNoCardsPlaceholder(columnList);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFiltersAndSort);
    }
    
    document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', applyFiltersAndSort);
    });

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', () => {
            if(searchInput) searchInput.value = '';
            
            document.querySelectorAll('.filter-checkbox').forEach(cb => cb.checked = false);
            
            document.querySelectorAll('.sort-cards-btn').forEach(btn => {
                btn.classList.remove('active-sort-asc', 'active-sort-desc');
                btn.innerHTML = btn.innerHTML.replace(/ ▲| ▼/, ''); 
            });
            columnSortStates = {}; 

            applyFiltersAndSort();
        });
    }
    
    document.querySelectorAll('.sort-cards-btn').forEach(button => {
        button.addEventListener('click', function() {
            const columnId = this.dataset.columnId;
            const sortBy = this.dataset.sortBy; 

            let currentSortOrder = columnSortStates[columnId] || 'none';
            let nextSortOrder = 'asc';

            if (currentSortOrder === 'asc') {
                nextSortOrder = 'desc';
            } else if (currentSortOrder === 'desc') {
                nextSortOrder = 'none'; 
            }
            
            columnSortStates[columnId] = nextSortOrder;

            document.querySelectorAll(`.sort-cards-btn[data-column-id="${columnId}"]`).forEach(btn => {
                btn.classList.remove('active-sort-asc', 'active-sort-desc');
                btn.innerHTML = btn.innerHTML.replace(/ ▲| ▼/, ''); 
            });

            if (nextSortOrder === 'asc') {
                this.classList.add('active-sort-asc');
                this.innerHTML += ' ▲';
            } else if (nextSortOrder === 'desc') {
                this.classList.add('active-sort-desc');
                this.innerHTML += ' ▼';
            }
            applyFiltersAndSort();
        });
    });


    const cardLists = document.querySelectorAll('.card-list');
    const csrfTokenForDrag = csrfToken; 

    cardLists.forEach(list => {
        Sortable.create(list, {
            group: 'cards',
            animation: 150,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            draggable: '.draggable-card',
            onEnd: function (evt) {
                const itemEl = evt.item;
                const toList = evt.to;
                const fromList = evt.from;
                const oldIndex = evt.oldDraggableIndex;

                const cardId = itemEl.getAttribute('data-card-id');
                const newColumnId = toList.getAttribute('data-column-id');

                const toColumnIdSort = toList.dataset.columnId;
                const fromColumnIdSort = fromList.dataset.columnId;
                
                [toColumnIdSort, fromColumnIdSort].forEach(colId => {
                    if (columnSortStates[colId] && columnSortStates[colId] !== 'none') {
                        columnSortStates[colId] = 'none';
                        const sortBtn = document.querySelector(`.sort-cards-btn[data-column-id="${colId}"]`);
                        if (sortBtn) {
                            sortBtn.classList.remove('active-sort-asc', 'active-sort-desc');
                            sortBtn.innerHTML = sortBtn.innerHTML.replace(/ ▲| ▼/, '');
                        }
                    }
                });


                updateNoCardsPlaceholder(toList);
                updateNoCardsPlaceholder(fromList);

                const payload = { new_column_id: newColumnId };

                if (!csrfTokenForDrag) {
                    console.error('CSRF token not found for drag-and-drop.');
                    alert('Ошибка: CSRF токен. Обновите страницу.');
                    fromList.insertBefore(itemEl, fromList.children[oldIndex]); 
                    updateNoCardsPlaceholder(toList);
                    updateNoCardsPlaceholder(fromList);
                    return;
                }

                fetch(`/api/cards/${cardId}/move`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfTokenForDrag
                    },
                    body: JSON.stringify(payload)
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => {
                            throw new Error(errData.error || `Request failed ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (!data.success) {
                        console.error('Failed to move card (API):', data.error || data.message);
                        fromList.insertBefore(itemEl, fromList.children[oldIndex]);
                        updateNoCardsPlaceholder(toList);
                        updateNoCardsPlaceholder(fromList);
                        alert('Ошибка перемещения: ' + (data.error || data.message || 'Неизвестная ошибка'));
                    } else {
                        // applyFiltersAndSort(); // Re-apply filters if necessary
                    }
                })
                .catch(error => {
                    console.error('Error during fetch for card move:', error);
                    fromList.insertBefore(itemEl, fromList.children[oldIndex]);
                    updateNoCardsPlaceholder(toList);
                    updateNoCardsPlaceholder(fromList);
                    alert('Критическая ошибка перемещения. (' + error.message + ')');
                });
            }
        });
    });
    function updateNoCardsPlaceholder(listElement) {
        if (!listElement) return;
        let placeholder = listElement.querySelector('.no-cards-placeholder');
        const cardsInList = Array.from(listElement.querySelectorAll('.draggable-card')).filter(card => card.style.display !== 'none').length;


        if (cardsInList === 0) {
            if (!placeholder) {
                placeholder = document.createElement('div');
                placeholder.className = 'list-group-item text-muted small fst-italic no-cards-placeholder';
                listElement.appendChild(placeholder);
            }
            placeholder.textContent = 'Нет карточек (или не соответствуют фильтру)';
            placeholder.style.display = 'block';
        } else {
            if (placeholder) {
                placeholder.style.display = 'none';
            }
        }
    }
    cardLists.forEach(list => {
        updateNoCardsPlaceholder(list);
    });
    applyFiltersAndSort(); 
});