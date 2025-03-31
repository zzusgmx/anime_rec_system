// 量子级动漫推荐系统 - 评论回复功能
// 处理评论回复、点赞等交互功能

class CommentInteractionManager {
  constructor() {
    this.apiEndpoints = {
      addReply: '/recommendations/comments/reply/',
      getReplies: '/recommendations/comments/replies/',
      toggleLike: '/recommendations/comments/like/',
      updateComment: '/recommendations/comments/update/',
      deleteComment: '/recommendations/comments/delete/'
    };

    // 评论面板中是否有未保存的编辑
    this.hasUnsavedChanges = false;

    console.log('[QUANTUM-COMMENT] 评论交互管理器初始化完成');

    // 绑定事件
    this.bindEvents();
  }

  // 获取CSRF令牌
  getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           document.cookie.split('; ')
               .find(row => row.startsWith('csrftoken='))
               ?.split('=')[1];
  }

  // 绑定所有事件处理器
  bindEvents() {
    document.addEventListener('DOMContentLoaded', () => {
      // 点赞评论
      document.addEventListener('click', e => {
        const likeBtn = e.target.closest('.comment-like-btn');
        if (likeBtn) {
          e.preventDefault();
          const commentId = likeBtn.dataset.commentId;
          this.toggleLike(commentId, likeBtn);
        }
      });

      // 回复评论
      document.addEventListener('click', e => {
        const replyBtn = e.target.closest('.reply-btn');
        if (replyBtn) {
          e.preventDefault();
          const commentId = replyBtn.dataset.commentId;
          const username = replyBtn.dataset.username;
          this.showReplyForm(commentId, username);
        }
      });

      // 取消回复
      document.addEventListener('click', e => {
        const cancelBtn = e.target.closest('.cancel-reply');
        if (cancelBtn) {
          e.preventDefault();
          const commentId = cancelBtn.dataset.commentId;
          this.hideReplyForm(commentId);
        }
      });

      // 提交回复
      document.addEventListener('click', e => {
        const submitBtn = e.target.closest('.submit-reply');
        if (submitBtn) {
          e.preventDefault();
          const commentId = submitBtn.dataset.commentId;
          this.submitReply(commentId);
        }
      });

      // 显示回复列表
      document.addEventListener('click', e => {
        const showRepliesBtn = e.target.closest('.show-replies');
        if (showRepliesBtn) {
          e.preventDefault();
          const commentId = showRepliesBtn.dataset.commentId;
          this.toggleReplies(commentId, showRepliesBtn);
        }
      });

      // 编辑评论
      document.addEventListener('click', e => {
        const editBtn = e.target.closest('.edit-comment');
        if (editBtn) {
          e.preventDefault();
          const commentId = editBtn.dataset.commentId;
          this.showEditForm(commentId);
        }
      });

      // 取消编辑
      document.addEventListener('click', e => {
        const cancelBtn = e.target.closest('.cancel-edit');
        if (cancelBtn) {
          e.preventDefault();
          const commentId = cancelBtn.dataset.commentId;
          this.hideEditForm(commentId);
        }
      });

      // 保存编辑
      document.addEventListener('click', e => {
        const saveBtn = e.target.closest('.save-edit');
        if (saveBtn) {
          e.preventDefault();
          const commentId = saveBtn.dataset.commentId;
          this.saveEdit(commentId);
        }
      });

      // 删除评论
      document.addEventListener('click', e => {
        const deleteBtn = e.target.closest('.delete-comment');
        if (deleteBtn) {
          e.preventDefault();
          const commentId = deleteBtn.dataset.commentId;
          this.confirmDeleteComment(commentId);
        }
      });

      // 离开页面前确认是否有未保存的编辑
      window.addEventListener('beforeunload', e => {
        if (this.hasUnsavedChanges) {
          e.preventDefault();
          e.returnValue = '您有未保存的评论修改，确定要离开页面吗？';
          return e.returnValue;
        }
      });
    });
  }

  // 切换评论点赞状态
async toggleLike(commentId, button) {
  if (!commentId || !button) return;

  try {
    // 获取当前状态
    const wasActive = button.classList.contains('active');
    const likeCountElement = button.querySelector('.like-count');
    const currentCount = parseInt(likeCountElement.textContent);

    // 仅更新按钮外观，不立即更新计数
    button.classList.toggle('active');
    button.querySelector('i').classList.toggle('far');
    button.querySelector('i').classList.toggle('fas');

    // 如果是点赞（不是取消点赞），添加动画效果
    if (!wasActive) {
      button.querySelector('i').classList.add('heartBeat');
      setTimeout(() => {
        button.querySelector('i').classList.remove('heartBeat');
      }, 1000);
    }

    // 发送请求
    const response = await fetch(`${this.apiEndpoints.toggleLike}${commentId}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken()
      },
      credentials: 'same-origin'
    });

    if (!response.ok) {
      throw new Error('点赞请求失败');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '点赞操作失败');
    }

    // 只使用服务器返回的实际值更新UI
    likeCountElement.textContent = data.like_count;

  } catch (error) {
    console.error('[QUANTUM-COMMENT] 点赞操作失败:', error);

    // 回滚UI
    button.classList.toggle('active');
    button.querySelector('i').classList.toggle('far');
    button.querySelector('i').classList.toggle('fas');

    // 显示错误通知
    this.showNotification('点赞操作失败，请稍后再试', 'error');
  }
}

  // 显示回复表单
  showReplyForm(commentId, username) {
    // 隐藏所有其他回复表单
    document.querySelectorAll('.reply-form-container').forEach(form => {
      form.classList.add('d-none');
    });

    // 显示当前回复表单
    const formContainer = document.getElementById(`reply-form-${commentId}`);
    if (formContainer) {
      formContainer.classList.remove('d-none');
      const textarea = formContainer.querySelector('textarea');
      if (textarea) {
        textarea.placeholder = `回复 @${username}...`;
        textarea.focus();
      }
    }
  }

  // 隐藏回复表单
  hideReplyForm(commentId) {
    const formContainer = document.getElementById(`reply-form-${commentId}`);
    if (formContainer) {
      formContainer.classList.add('d-none');
      const textarea = formContainer.querySelector('textarea');
      if (textarea) {
        textarea.value = '';
      }
    }
  }

  // 提交回复
  async submitReply(commentId) {
    const formContainer = document.getElementById(`reply-form-${commentId}`);
    if (!formContainer) return;

    const textarea = formContainer.querySelector('textarea');
    if (!textarea) return;

    const content = textarea.value.trim();

    if (!content) {
      this.showNotification('请输入回复内容', 'warning');
      textarea.focus();
      return;
    }

    try {
      // 禁用按钮，显示加载状态
      const submitBtn = formContainer.querySelector('.submit-reply');
      const cancelBtn = formContainer.querySelector('.cancel-reply');

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> 提交中...';
      }

      if (cancelBtn) {
        cancelBtn.disabled = true;
      }

      // 发送请求
      const response = await fetch(`${this.apiEndpoints.addReply}${commentId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify({ content }),
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error('提交回复失败');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '回复提交失败');
      }

      // 清空表单
      textarea.value = '';

      // 隐藏回复表单
      this.hideReplyForm(commentId);

      // 更新回复计数并显示回复
      this.updateReplyCount(commentId, data.reply_count);

      // 加载所有回复
      await this.loadReplies(commentId);

      // 显示成功通知
      this.showNotification('回复已提交', 'success');

    } catch (error) {
      console.error('[QUANTUM-COMMENT] 提交回复失败:', error);
      this.showNotification(error.message || '回复提交失败，请稍后再试', 'error');
    } finally {
      // 恢复按钮状态
      const submitBtn = formContainer.querySelector('.submit-reply');
      const cancelBtn = formContainer.querySelector('.cancel-reply');

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 发送回复';
      }

      if (cancelBtn) {
        cancelBtn.disabled = false;
      }
    }
  }

  // 更新回复计数
  updateReplyCount(commentId, replyCount) {
    const repliesToggle = document.querySelector(`.replies-toggle[data-comment-id="${commentId}"]`);

    if (!repliesToggle) {
      // 创建回复计数区域
      const comment = document.getElementById(`comment-${commentId}`);
      if (comment) {
        const newToggle = document.createElement('div');
        newToggle.className = 'replies-toggle';
        newToggle.dataset.commentId = commentId;
        newToggle.innerHTML = `
          <button class="btn btn-sm btn-link show-replies" data-comment-id="${commentId}">
            <i class="fas fa-comments"></i> 
            显示全部 ${replyCount} 条回复
          </button>
        `;

        const repliesContainer = comment.querySelector('.replies-container');
        if (repliesContainer) {
          repliesContainer.before(newToggle);
        }
      }
    } else {
      // 更新现有回复计数
      const showBtn = repliesToggle.querySelector('.show-replies');
      if (showBtn) {
        showBtn.innerHTML = `<i class="fas fa-comments"></i> 显示全部 ${replyCount} 条回复`;
      }

      // 如果回复计数为0，隐藏回复区域
      if (replyCount === 0) {
        repliesToggle.style.display = 'none';
      } else {
        repliesToggle.style.display = 'block';
      }
    }
  }

  // 切换显示/隐藏回复
  async toggleReplies(commentId, button) {
    const repliesContainer = document.getElementById(`replies-${commentId}`);
    if (!repliesContainer) return;

    // 检查是否已经加载过回复
    if (repliesContainer.innerHTML.trim() === '') {
      // 显示加载状态
      repliesContainer.innerHTML = `
        <div class="text-center py-3">
          <div class="quantum-spinner"></div>
          <p class="mt-2">加载回复中...</p>
        </div>
      `;

      button.disabled = true;
      button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> 加载中...';

      try {
        await this.loadReplies(commentId);

        // 更改按钮文本
        button.innerHTML = '<i class="fas fa-chevron-up"></i> 收起回复';
      } catch (error) {
        console.error('[QUANTUM-COMMENT] 加载回复失败:', error);

        repliesContainer.innerHTML = `
          <div class="text-center py-3 text-danger">
            <i class="fas fa-exclamation-circle"></i>
            <p>加载回复失败，请稍后再试</p>
          </div>
        `;

        button.innerHTML = '<i class="fas fa-sync"></i> 重试加载回复';
      } finally {
        button.disabled = false;
      }
    } else {
      // 已加载过回复，切换显示/隐藏
      if (repliesContainer.style.display === 'none') {
        repliesContainer.style.display = 'block';
        button.innerHTML = '<i class="fas fa-chevron-up"></i> 收起回复';
      } else {
        repliesContainer.style.display = 'none';
        button.innerHTML = '<i class="fas fa-comments"></i> 显示回复';
      }
    }
  }

  // 加载评论回复
  async loadReplies(commentId) {
    const repliesContainer = document.getElementById(`replies-${commentId}`);
    if (!repliesContainer) return;

    try {
      const response = await fetch(`${this.apiEndpoints.getReplies}${commentId}/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error('获取回复失败');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '获取回复数据失败');
      }

      // 渲染回复
      if (data.replies && data.replies.length > 0) {
        repliesContainer.innerHTML = data.replies;

        // 添加动画效果
        repliesContainer.querySelectorAll('.comment-reply').forEach((reply, index) => {
          reply.style.opacity = '0';
          reply.style.transform = 'translateY(10px)';

          setTimeout(() => {
            reply.style.transition = 'all 0.3s ease';
            reply.style.opacity = '1';
            reply.style.transform = 'translateY(0)';
          }, index * 100);
        });
      } else {
        repliesContainer.innerHTML = `
          <div class="text-center py-3 text-muted">
            <p>暂无回复</p>
          </div>
        `;
      }
    } catch (error) {
      console.error('[QUANTUM-COMMENT] 加载回复失败:', error);
      throw error;
    }
  }

  // 显示编辑表单
  showEditForm(commentId) {
    const contentContainer = document.getElementById(`comment-content-${commentId}`);
    const editForm = document.getElementById(`comment-edit-form-${commentId}`);

    if (contentContainer && editForm) {
      // 显示编辑表单，隐藏内容
      contentContainer.classList.add('d-none');
      editForm.classList.remove('d-none');

      // 设置焦点
      const textarea = editForm.querySelector('textarea');
      if (textarea) {
        textarea.focus();
        // 将光标移动到文本末尾
        textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
      }

      // 标记有未保存的更改
      this.hasUnsavedChanges = true;
    }
  }

  // 隐藏编辑表单
  hideEditForm(commentId) {
    const contentContainer = document.getElementById(`comment-content-${commentId}`);
    const editForm = document.getElementById(`comment-edit-form-${commentId}`);

    if (contentContainer && editForm) {
      // 隐藏编辑表单，显示内容
      contentContainer.classList.remove('d-none');
      editForm.classList.add('d-none');

      // 标记无未保存的更改
      this.hasUnsavedChanges = false;
    }
  }

  // 保存评论编辑
  async saveEdit(commentId) {
    const editForm = document.getElementById(`comment-edit-form-${commentId}`);
    if (!editForm) return;

    const textarea = editForm.querySelector('textarea');
    if (!textarea) return;

    const content = textarea.value.trim();

    if (!content) {
      this.showNotification('评论内容不能为空', 'warning');
      textarea.focus();
      return;
    }

    try {
      // 禁用按钮，显示加载状态
      const saveBtn = editForm.querySelector('.save-edit');
      const cancelBtn = editForm.querySelector('.cancel-edit');

      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中...';
      }

      if (cancelBtn) {
        cancelBtn.disabled = true;
      }

      // 发送请求
      const response = await fetch(`${this.apiEndpoints.updateComment}${commentId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify({ content }),
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error('保存评论失败');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '评论更新失败');
      }

      // 更新评论内容
      const contentContainer = document.getElementById(`comment-content-${commentId}`);
      if (contentContainer) {
        contentContainer.innerHTML = data.html || content.replace(/\n/g, '<br>');
      }

      // 隐藏编辑表单
      this.hideEditForm(commentId);

      // 显示成功通知
      this.showNotification('评论已更新', 'success');

      // 标记无未保存的更改
      this.hasUnsavedChanges = false;

    } catch (error) {
      console.error('[QUANTUM-COMMENT] 保存评论失败:', error);
      this.showNotification(error.message || '评论保存失败，请稍后再试', 'error');
    } finally {
      // 恢复按钮状态
      const saveBtn = editForm.querySelector('.save-edit');
      const cancelBtn = editForm.querySelector('.cancel-edit');

      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = '保存';
      }

      if (cancelBtn) {
        cancelBtn.disabled = false;
      }
    }
  }

  // 确认删除评论
  confirmDeleteComment(commentId) {
    if (confirm('确定要删除这条评论吗？此操作无法撤销。')) {
      this.deleteComment(commentId);
    }
  }

  // 删除评论
  async deleteComment(commentId) {
    try {
      // 发送请求
      const response = await fetch(`${this.apiEndpoints.deleteComment}${commentId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error('删除评论失败');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '评论删除失败');
      }

      // 从DOM中移除评论
      const commentElement = document.getElementById(`comment-${commentId}`);
      if (commentElement) {
        // 添加淡出动画效果
        commentElement.style.transition = 'all 0.5s ease';
        commentElement.style.opacity = '0';
        commentElement.style.transform = 'translateY(-20px)';

        // 动画完成后删除元素
        setTimeout(() => {
          commentElement.remove();
        }, 500);
      }

      // 显示成功通知
      this.showNotification('评论已删除', 'success');

    } catch (error) {
      console.error('[QUANTUM-COMMENT] 删除评论失败:', error);
      this.showNotification(error.message || '评论删除失败，请稍后再试', 'error');
    }
  }

  // 显示通知
  showNotification(message, type = 'info') {
    if (window.showToast) {
      // 如果有全局通知函数，使用它
      window.showToast(message, type);
    } else {
      // 简单的通知实现
      const notificationContainer = document.getElementById('notificationContainer');
      let container = notificationContainer;

      if (!container) {
        // 创建通知容器
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
      }

      // 创建通知元素
      const notification = document.createElement('div');
      notification.className = `alert alert-${type} alert-dismissible fade show`;
      notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;

      // 添加到容器
      container.appendChild(notification);

      // 3秒后自动关闭
      setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
          notification.remove();
        }, 300);
      }, 3000);
    }
  }
}

// 初始化评论交互管理器
window.commentInteractionManager = new CommentInteractionManager();