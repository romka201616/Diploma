document.addEventListener('DOMContentLoaded', function () {
    var cardDetailModalEl = document.getElementById('cardDetailModal');
    var cardModal = bootstrap.Modal.getInstance(cardDetailModalEl) || new bootstrap.Modal(cardDetailModalEl);
    var currentCardId = null; 
    var currentBoardId = null; // Мы можем получить это из URL или передать в data-атрибут

    // Пытаемся получить board_id из URL, если он там есть (например, /boards/ID/...)
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length >= 3 && pathParts[1] === 'boards') {
        const boardIdFromUrl = parseInt(pathParts[2], 10);
        if (!isNaN(boardIdFromUrl)) {
            currentBoardId = boardIdFromUrl;
        }
    }
    // Или, если у вас есть элемент с data-board-id на странице, можно взять оттуда
    // const boardContainer = document.getElementById('boardColumnsContainer'); // Пример
    // if (boardContainer && boardContainer.dataset.boardId) {
    //     currentBoardId = boardContainer.dataset.boardId;
    // }


    var csrfTokenInput = document.querySelector('form input[name="csrf_token"]'); 
    var csrfToken = csrfTokenInput ? csrfTokenInput.value : null;
    if (!csrfToken) {
        console.error("CSRF Token not found on the page for AJAX!");
    }

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
                // Предполагаем, что URL аватара хранится в data-атрибуте option,
                // который заполняется при открытии модалки
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

        function openModalWithCard(cardIdToOpen) {
            const cardElement = document.getElementById(`card-${cardIdToOpen}`);
            if (cardElement) {
                // Имитируем клик по карточке, чтобы вызвать стандартный обработчик Bootstrap
                // и наш 'show.bs.modal' listener
                cardElement.dispatchEvent(new Event('click', { bubbles: true }));
                // Убедимся, что модальное окно действительно открывается
                if (!cardModalEl.classList.contains('show')) {
                     cardModal.show(cardElement); // Принудительно открываем, передавая relatedTarget
                }
            } else {
                console.warn(`Card element with ID card-${cardIdToOpen} not found to open modal.`);
            }
        }


        cardDetailModalEl.addEventListener('show.bs.modal', function (event) {
            var cardElement = event.relatedTarget; // Элемент, который вызвал модалку
            if (!cardElement || !cardElement.classList.contains('draggable-card')) {
                // Если модалка открывается не по клику на карточку (например, по URL),
                // cardElement может быть undefined. В этом случае currentCardId уже должен быть установлен.
                if (!currentCardId) {
                    console.error("Modal opened without a card context.");
                    // Возможно, стоит закрыть модалку или показать ошибку
                    // cardModal.hide();
                    return;
                }
                // Загружаем данные для currentCardId, если cardElement не определен
                // Это нужно, если мы открываем модалку по URL напрямую
                // Потребуется дополнительный AJAX-запрос для получения данных карточки
                // Пока что оставим эту логику для открытия по клику
            } else {
                 currentCardId = cardElement.getAttribute('data-card-id'); 
            }

            // Обновляем URL без перезагрузки страницы, если currentBoardId и currentCardId известны
            if (currentBoardId && currentCardId) {
                const newUrl = `/boards/${currentBoardId}/cards/${currentCardId}`;
                history.pushState({cardId: currentCardId}, `Карточка ${currentCardId}`, newUrl);
            }


            var cardTitle = cardElement ? cardElement.getAttribute('data-card-title') : modalTitleField.value; // Фоллбэк на текущее значение
            var cardDescription = cardElement ? cardElement.getAttribute('data-card-description') : modalDescriptionField.value;
            var editUrl = cardElement ? cardElement.getAttribute('data-edit-url') : modalForm.action;
            var deleteUrl = cardElement ? cardElement.getAttribute('data-delete-url') : deleteForm.action;
            var cardAssigneesJson = cardElement ? cardElement.getAttribute('data-card-assignees') : '[]';
            
            var currentAssignees = [];
            try {
                currentAssignees = JSON.parse(cardAssigneesJson);
            } catch (e) {
                console.error("Error parsing card assignees JSON:", e, cardAssigneesJson);
            }
            var currentAssigneeIds = currentAssignees.map(a => a.id.toString());

            modalForm.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
            modalForm.querySelectorAll('.invalid-feedback').forEach(el => el.textContent = '');
            if(modalCommentTextError) modalCommentTextError.textContent = '';
            if(modalCommentText) modalCommentText.classList.remove('is-invalid');


            modalLabel.textContent = 'Карточка: ' + cardTitle;
            modalTitleField.value = cardTitle;
            modalDescriptionField.value = cardDescription;
            modalForm.action = editUrl;
            deleteForm.action = deleteUrl;
            
            if (modalAssigneesSelect) {
                Array.from(modalAssigneesSelect.options).forEach(option => {
                    option.selected = currentAssigneeIds.includes(option.value);
                    const assigneeData = currentAssignees.find(a => a.id.toString() === option.value);
                    if (assigneeData && assigneeData.avatar_url) {
                        option.dataset.avatarUrl = assigneeData.avatar_url;
                    } else {
                        delete option.dataset.avatarUrl;
                    }
                });
                updateModalAssigneesPreview();
            }
            

            let deleteCsrfInput = deleteForm.querySelector('input[name="csrf_token"]');
             if (deleteCsrfInput && csrfToken) {
                 deleteCsrfInput.value = csrfToken;
             } else if (!csrfToken) {
                 console.error("CSRF Token missing for delete form in modal.");
             }
            
            fetchComments(currentCardId);
            if (addCommentForm) {
                addCommentForm.action = `/cards/${currentCardId}/comments/add`;
                let commentCsrf = addCommentForm.querySelector('input[name="csrf_token"]');
                if (commentCsrf && csrfToken) {
                    commentCsrf.value = csrfToken;
                } else if (!commentCsrf && csrfToken){
                    commentCsrf = document.createElement('input');
                    commentCsrf.type = 'hidden';
                    commentCsrf.name = 'csrf_token';
                    commentCsrf.value = csrfToken;
                    addCommentForm.appendChild(commentCsrf);
                }
            }
        });
        
        cardDetailModalEl.addEventListener('hidden.bs.modal', function () {
            // currentCardId = null; // Не сбрасываем, если хотим сохранить состояние для URL
            if (commentsListContainer) commentsListContainer.innerHTML = ''; 
            if (addCommentForm) addCommentForm.reset(); 
            if (modalCommentText) modalCommentText.classList.remove('is-invalid');
            if (modalCommentTextError) modalCommentTextError.textContent = '';

            // При закрытии модалки возвращаем URL к доске
            if (currentBoardId) {
                const boardUrl = `/boards/${currentBoardId}`;
                history.pushState({boardId: currentBoardId}, `Доска ${currentBoardId}`, boardUrl);
            }
            // currentCardId = null; // Теперь можно сбросить
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
             let deleteCsrfToken = deleteForm.querySelector('input[name="csrf_token"]').value;
             if (!deleteCsrfToken && csrfToken) deleteCsrfToken = csrfToken;

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
                      cardModal.hide(); // Закрываем модалку после удаления
                      const cardIdToDelete = deleteForm.action.split('/').filter(Boolean).pop();
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
            for (const field in errors) {
                const inputElement = targetForm.querySelector(`[name="${field}"], #${field}`);
                const errorElementId = `modal${field.charAt(0).toUpperCase() + field.slice(1)}Error`;
                const errorElement = document.getElementById(errorElementId) || targetForm.querySelector(`.invalid-feedback[data-field-error="${field}"]`);
                
                if (inputElement) {
                    inputElement.classList.add('is-invalid');
                    if (inputElement.tagName === 'SELECT' && inputElement.multiple) {
                        let feedback = inputElement.nextElementSibling; 
                        if (feedback && (feedback.classList.contains('invalid-feedback') || feedback.id === errorElementId)) {
                            feedback.textContent = errors[field];
                        }
                    }
                }
                 if (errorElement) {
                     errorElement.textContent = errors[field];
                 }
            }
        }

        function updateCardDisplay(cardData) {
            const cardElement = document.getElementById(`card-${cardData.id}`);
            if (!cardElement) return;

            cardElement.setAttribute('data-card-title', cardData.title);
            cardElement.setAttribute('data-card-description', cardData.description || '');
            cardElement.setAttribute('data-card-assignees', JSON.stringify(cardData.assignees || []));

            const titleDisplay = cardElement.querySelector('.card-title-display');
            if (titleDisplay) titleDisplay.textContent = cardData.title;
            // Обновляем заголовок модального окна, если оно открыто для этой карточки
            if (currentCardId == cardData.id && modalLabel.textContent.startsWith('Карточка:')) {
                 modalLabel.textContent = 'Карточка: ' + cardData.title;
            }


            const descriptionIndicator = cardElement.querySelector('.card-description-indicator');
            const detailsContainer = cardElement.querySelector('.card-details-display');

            if (cardData.description) {
                if (descriptionIndicator) descriptionIndicator.style.display = 'inline';
                else if(detailsContainer) { 
                    const newIndicator = document.createElement('small');
                    newIndicator.className = 'text-muted card-description-indicator me-2';
                    newIndicator.title = 'Есть описание';
                    newIndicator.innerHTML = '📄';
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
                            <small class="fw-bold">${comment.author.username}</small>
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
                    } else {
                        console.error("Could not find commentId or formElement for saving edited comment.");
                    }
                } else if (target.classList.contains('cancel-edit-comment-btn')) {
                     const formElement = target.closest('.edit-comment-form');
                     const commentId = formElement ? formElement.dataset.commentId : null;
                     if (commentId) { 
                        hideEditCommentForm(commentId);
                     } else {
                        console.error("Could not find commentId for cancelling edit.");
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
            if(!formElement || !commentId) { 
                console.error("Form element or commentId is missing for saving comment.");
                return;
            }
            const formData = new FormData(formElement);
            
            if (!formData.has('csrf_token') && csrfToken) {
                 formData.append('csrf_token', csrfToken);
            }

            fetch(`/comments/${commentId}/edit`, {
                method: 'POST',
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                body: formData
            })
            .then(response => { 
                if (!response.ok) { 
                    return response.text().then(text => { 
                        throw new Error(`Server responded with ${response.status}: ${text}`);
                    });
                }
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
                    } else {
                        alert("Ошибка валидации: " + JSON.stringify(body.errors));
                    }
                } else { 
                     alert('Ошибка редактирования комментария: ' + (body.error || body.message || "Неизвестная ошибка"));
                }
            })
            .catch(error => {
                console.error("Error editing comment:", error);
                alert("Ошибка при редактировании комментария. " + error.message);
            });
        }
        
        function handleDeleteCommentClick(commentId) {
            if (!confirm("Удалить этот комментарий?")) return;
            if (!csrfToken) {
                alert("Ошибка: CSRF токен не найден.");
                return;
            }

            fetch(`/comments/${commentId}/delete`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken 
                }
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
            return unsafe
                 .toString()
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        }

        // --- Обработка URL и открытие модалки при загрузке страницы ---
        function checkUrlAndOpenModal() {
            const path = window.location.pathname;
            const match = path.match(/\/boards\/(\d+)\/cards\/(\d+)/);
            if (match) {
                const boardId = match[1];
                const urlCardId = match[2]; // Переименовал для ясности
                if (boardId && urlCardId) {
                    if (!currentBoardId) currentBoardId = parseInt(boardId, 10);
                    currentCardId = urlCardId;

                    // Логика для загрузки данных карточки и открытия модалки, если карточки нет на странице
                    const cardElement = document.getElementById(`card-${urlCardId}`);
                    if (cardElement) {
                        cardModal.show(cardElement); // Используем существующий элемент
                    } else {
                        // Карточки нет на видимой части доски, или прямой заход по URL
                        // Загружаем данные карточки и потом показываем модалку
                        fetch(`/cards/${urlCardId}/edit`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                            .then(response => {
                                if (!response.ok) throw new Error(`Failed to fetch card data: ${response.status}`);
                                return response.json();
                            })
                            .then(data => {
                                if (data.success && data.card) {
                                    // Заполняем поля модалки вручную из полученных данных
                                    modalLabel.textContent = 'Карточка: ' + data.card.title;
                                    modalTitleField.value = data.card.title;
                                    modalDescriptionField.value = data.card.description;
                                    // Убедимся, что action для форм установлен правильно
                                    modalForm.action = `/cards/${urlCardId}/edit`;
                                    deleteForm.action = `/cards/${urlCardId}/delete`;

                                    if (modalAssigneesSelect && data.card.assignees) { // Проверка на существование assignees
                                        const assigneeIds = data.card.assignee_ids || [];
                                        Array.from(modalAssigneesSelect.options).forEach(option => {
                                            option.selected = assigneeIds.includes(parseInt(option.value));
                                            const assigneeData = (data.card.assignees || []).find(a => a.id.toString() === option.value);
                                            if (assigneeData && assigneeData.avatar_url) {
                                                option.dataset.avatarUrl = assigneeData.avatar_url;
                                            } else {
                                                delete option.dataset.avatarUrl;
                                            }
                                        });
                                        updateModalAssigneesPreview();
                                    }

                                    // Устанавливаем currentCardId здесь, так как он подтвержден
                                    currentCardId = data.card.id.toString();

                                    fetchComments(currentCardId);
                                    if (addCommentForm) {
                                        addCommentForm.action = `/cards/${currentCardId}/comments/add`;
                                        // Убедимся, что CSRF токен есть в форме добавления комментария
                                        let commentCsrf = addCommentForm.querySelector('input[name="csrf_token"]');
                                        if (commentCsrf && csrfToken) {
                                            commentCsrf.value = csrfToken;
                                        } else if (!commentCsrf && csrfToken) {
                                            commentCsrf = document.createElement('input');
                                            commentCsrf.type = 'hidden';
                                            commentCsrf.name = 'csrf_token';
                                            commentCsrf.value = csrfToken;
                                            addCommentForm.appendChild(commentCsrf);
                                        }
                                    }

                                    cardModal.show();
                                } else {
                                    console.error("Failed to fetch card data or card not found:", data.error);
                                    if (currentBoardId) history.replaceState(null, '', `/boards/${currentBoardId}`);
                                }
                            })
                            .catch(err => {
                                console.error("Error fetching card data for direct URL open:", err);
                                if (currentBoardId) history.replaceState(null, '', `/boards/${currentBoardId}`);
                            });
                    }
                }
            }
        }
        checkUrlAndOpenModal();
        window.addEventListener('popstate', function (event) {
            // При изменении истории (назад/вперед) проверяем URL и открываем/закрываем модалку
            // Если event.state есть, это может быть наше состояние, которое мы сохранили
            // Если нет, то просто парсим URL
            const path = window.location.pathname;
            const match = path.match(/\/boards\/(\d+)\/cards\/(\d+)/);
            if (match) {
                checkUrlAndOpenModal();
            } else {
                // Если URL не содержит /cards/ID, значит модалка должна быть закрыта
                if (cardModalEl.classList.contains('show')) {
                    cardModal.hide();
                }
            }
        });


    } 

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
        const cardsInList = listElement.querySelectorAll('.draggable-card').length;

        if (cardsInList === 0) {
            if (!placeholder) {
                placeholder = document.createElement('div');
                placeholder.className = 'list-group-item text-muted small fst-italic no-cards-placeholder';
                placeholder.textContent = 'Нет карточек';
                listElement.appendChild(placeholder);
            }
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
});