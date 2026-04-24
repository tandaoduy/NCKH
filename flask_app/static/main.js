/**
 * JavaScript chính cho hệ thống gợi ý kế hoạch học tập
 * Logic phía giao diện người dùng.
 */

// ========== BIẾN TOÀN CỤC ==========
let allStudents = [];
let selectedStudent = null;

// ========== KHỞI TẠO ==========
document.addEventListener('DOMContentLoaded', function () {
    console.log('Đang khởi tạo trang...');
    // Nếu trang đã có logic load sinh viên riêng (như students.html) thì không chạy load chung ở đây
    if (document.getElementById('studentSelect') && typeof window.currentStudent === 'undefined') {
        loadAllStudents();
    }
    initNavbarScroll();
    initFlashToasts();
});

// ========== HIỆU ỨNG CUỘN NAVBAR ==========
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            // Thêm class 'scrolled' khi người dùng cuộn trang
            if (window.scrollY > 20) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }
}

// ========== BƯỚC 1: TẢI DANH SÁCH SINH VIÊN ==========
async function loadAllStudents() {
    try {
        const response = await fetch('/api/students');
        const data = await response.json();

        if (data.success) {
            allStudents = data.data;
            console.log(`Đã nạp ${allStudents.length} sinh viên`);

            // Đổ dữ liệu vào ô chọn
            populateStudentSelect();
        } else {
            console.error('Lỗi khi nạp danh sách sinh viên:', data.error);
            showError('Không thể tải danh sách sinh viên');
        }
    } catch (error) {
        console.error('Lỗi khi gọi dữ liệu:', error);
        showError('Lỗi kết nối đến server');
    }
}

function populateStudentSelect() {
    const select = document.getElementById('studentSelect');
    if (!select) {
        return;
    }

    select.innerHTML = '<option value="">-- Chọn sinh viên --</option>';

    allStudents.forEach(student => {
        const option = document.createElement('option');
        option.value = student.student_id;
        option.text = `${student.student_id} - ${student.name}`;
        select.appendChild(option);
    });
}

// ========== BƯỚC 1: TÌM SINH VIÊN ==========
function searchStudent() {
    const searchInput = document.getElementById('studentSearch');
    const searchTerm = searchInput.value.trim().toUpperCase();

    if (!searchTerm) {
        showError('Vui lòng nhập mã sinh viên', 'warning');
        return;
    }

    // Tìm sinh viên
    const student = allStudents.find(s => s.student_id.toUpperCase() === searchTerm);
    if (student) {
        document.getElementById('studentSelect').value = student.student_id;
        onStudentSelected();
    } else {
        showError(`Không tìm thấy sinh viên: ${searchTerm}`);
    }
}

// ========== BƯỚC 2: CHỌN SINH VIÊN ==========
async function onStudentSelected() {
    const select = document.getElementById('studentSelect');
    const studentId = select.value;

    if (!studentId) {
        // Ẩn thông tin nếu chưa chọn sinh viên
        document.getElementById('studentProfileSection').style.display = 'none';
        document.getElementById('recommendationActionSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';

        const eligibleSection = document.getElementById('eligibleCoursesSection');
        if (eligibleSection) {
            eligibleSection.style.display = 'none';
        }
        return;
    }

    try {
        // Lấy hồ sơ chi tiết sinh viên
        const response = await fetch(`/api/students/${studentId}`);
        const data = await response.json();

        if (data.success) {
            selectedStudent = data.data;
            displayStudentProfile(selectedStudent);

            // Hiển thị thông tin và nút thao tác
            document.getElementById('studentProfileSection').style.display = 'block';
            document.getElementById('recommendationActionSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';

            const eligibleSection = document.getElementById('eligibleCoursesSection');
            if (eligibleSection) {
                eligibleSection.style.display = 'none';
            }
        } else {
            showError('Không thể tải thông tin sinh viên');
        }
    } catch (error) {
        console.error('Lỗi khi gọi dữ liệu:', error);
        showError('Lỗi tải thông tin sinh viên');
    }
}

// ========== BƯỚC 2: HIỂN THỊ HỒ SƠ SINH VIÊN ==========
function displayStudentProfile(student) {
    document.getElementById('profileStudentId').textContent = student.student_id;
    document.getElementById('profileName').textContent = student.name;
    document.getElementById('profileMajor').textContent = student.major || '-';
    document.getElementById('profileSpecialization').textContent = student.specialization || 'Chưa chọn';
    document.getElementById('profileGoal').textContent = translateStudyGoal(student.study_goal);
    document.getElementById('profileSemester').textContent = student.current_semester;
    document.getElementById('profileCredits').textContent = student.total_credits_accumulated;
    document.getElementById('profileMaxCredits').textContent = student.max_credits_to_register;
    document.getElementById('profileYearAdmitted').textContent = student.year_admitted;

    // Hiển thị môn đã học
    const passedCourses = student.passed_courses || [];
    document.getElementById('passedCoursesCount').textContent = `${passedCourses.length} môn`;
    const passedList = document.getElementById('passedCoursesList');
    passedList.innerHTML = '';
    passedCourses.forEach(course => {
        const badge = document.createElement('div');
        badge.className = 'course-badge';
        badge.textContent = course;
        passedList.appendChild(badge);
    });

    // Hiển thị môn chưa đạt
    const failedCourses = student.failed_courses || [];
    document.getElementById('failedCoursesCount').textContent = `${failedCourses.length} môn`;
    const failedList = document.getElementById('failedCoursesList');
    failedList.innerHTML = '';
    failedCourses.forEach(course => {
        const badge = document.createElement('div');
        badge.className = 'course-badge failed';
        badge.textContent = course;
        failedList.appendChild(badge);
    });
}

// ========== BƯỚC 3: TẠO GỢI Ý KẾ HOẠCH HỌC TẬP ==========
async function generateRecommendation() {
    if (!selectedStudent) {
        showError('Vui lòng chọn sinh viên', 'warning');
        return;
    }

    const generateBtn = document.getElementById('generateBtn');
    const spinnerDiv = document.getElementById('loadingSpinner');

    try {
        generateBtn.disabled = true;
        spinnerDiv.style.display = 'block';

        const response = await fetch('/api/recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                student_id: selectedStudent.student_id
            })
        });

        const result = await response.json();

        if (result.success) {
            displayRecommendationResults(result.data);
            document.getElementById('resultsSection').style.display = 'block';
        } else {
            const errorMsg = result.details ? result.details.join(', ') : result.error;
            showError(`Lỗi: ${errorMsg}`);
        }
    } catch (error) {
        console.error('Lỗi:', error);
        showError(`Lỗi kế nối: ${error.message}`);
    } finally {
        generateBtn.disabled = false;
        spinnerDiv.style.display = 'none';
    }
}

// ========== BƯỚC 4: HIỂN THỊ KẾT QUẢ GỢI Ý ==========
function displayRecommendationResults(data) {
    // Hiển thị danh sách môn đủ điều kiện học ngay dưới nút "Tạo kế hoạch học tập"
    displayEligibleCourses(data.eligible_courses || []);

    // Cập nhật thống kê tóm tắt
    const courses = data.recommended_courses || [];
    document.getElementById('resultTotalCourses').textContent = courses.length;
    document.getElementById('resultTotalCredits').textContent = data.total_recommended_credits || 0;

    // Tính học kỳ tiếp theo từ dữ liệu sinh viên
    document.getElementById('resultNextSemester').textContent = data.next_semester || '-';

    // Hiển thị bảng môn học - dùng đúng tbody ID
    const tableBody = document.getElementById('recommendedCoursesList');
    if (tableBody) {
        tableBody.innerHTML = '';

        courses.forEach((course, index) => {
            const row = document.createElement('tr');
            // Dữ liệu trả về: code, name, credits, heuristic_score, reasons (array)
            const reasonsText = (course.reasons && Array.isArray(course.reasons))
                ? course.reasons.join(', ')
                : '-';

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${course.code || '-'}</td>
                <td>${course.name || '-'}</td>
                <td>${course.credits || 0}</td>
                <td>${course.is_retake ? '<span class="status-badge status-retake">Học lại</span>' : `<span class="status-badge status-normal">Kỳ ${course.recommended_semester || data.next_semester || '-'}</span>`}</td>
                <td>${reasonsText}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    displayResultWarnings(data);
    displayResultInsights(data);
    // Hiển thị chi tiết thuật toán
    renderAlgorithmExplanation(data);
}

// ========== HÀM HỖ TRỢ ==========

function renderAlgorithmExplanation(data) {
    const section = document.getElementById('algorithmDetailsSection');
    const content = document.getElementById('algorithmDetailsContent');

    if (!section || !content) {
        return;
    }

    const parts = [];

    if (data && data.explanation) {
        parts.push(data.explanation);
    } else {
        if (data && data.beam_search_details) {
            parts.push(`Chi tiết chùm: ${data.beam_search_details}`);
        }
        if (data && data.heuristic_formula) {
            parts.push(`Công thức heuristic: ${data.heuristic_formula}`);
        }
        if (data && Array.isArray(data.warnings) && data.warnings.length) {
            parts.push(`Cảnh báo:\n- ${data.warnings.join('\n- ')}`);
        }
    }

    if (!parts.length) {
        section.style.display = 'none';
        content.innerHTML = '';
        return;
    }

    content.innerHTML = `<pre>${escapeHtml(parts.join('\n\n'))}</pre>`;
    section.style.display = 'block';
}

function displayResultWarnings(result) {
    const section = document.getElementById('resultWarningsSection');
    const list = document.getElementById('resultWarningsList');
    if (!section || !list) {
        return;
    }

    const warnings = [];
    if (result?.specialization_warning) {
        warnings.push(result.specialization_warning);
    }
    if (Array.isArray(result?.prerequisite_warnings)) {
        warnings.push(...result.prerequisite_warnings);
    }
    if (Array.isArray(result?.warnings)) {
        result.warnings.forEach(item => {
            if (item && !warnings.includes(item)) {
                warnings.push(item);
            }
        });
    }

    if (!warnings.length) {
        section.style.display = 'none';
        list.innerHTML = '';
        return;
    }

    list.innerHTML = warnings.map(item => `<div class="warning-item">${escapeHtml(item)}</div>`).join('');
    section.style.display = 'block';
}

function displayResultInsights(result) {
    const beamEl = document.getElementById('beamSearchSummary');
    const quotaEl = document.getElementById('quotaOverviewSummary');

    if (beamEl) {
        beamEl.innerHTML = result?.beam_search_details
            ? `<code>${escapeHtml(result.beam_search_details)}</code>`
            : '<span>-</span>';
    }

    if (quotaEl) {
        const quotas = result?.elective_target_quotas || {};
        const completed = result?.elective_completed_counts || {};
        const remaining = result?.elective_quota_remaining || {};
        const finalized = result?.finalized_elective_counts || {};

        const rows = ['general', 'physical', 'foundation', 'specialization'].map(key => {
            const label = {
                general: 'Đại cương',
                physical: 'Thể chất',
                foundation: 'Cơ sở ngành',
                specialization: 'Chuyên ngành',
            }[key] || key;

            return `
                <tr>
                    <td>${label}</td>
                    <td>${completed[key] ?? 0}</td>
                    <td>${quotas[key] ?? 0}</td>
                    <td>${remaining[key] ?? 0}</td>
                    <td>${finalized[key] ?? 0}</td>
                </tr>
            `;
        }).join('');

        quotaEl.innerHTML = `
            <table class="quota-table">
                <thead>
                    <tr>
                        <th>Danh mục</th>
                        <th>Đã hoàn</th>
                        <th>Mục tiêu</th>
                        <th>Còn thiếu</th>
                        <th>Đã chọn</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }
}

function displayEligibleCourses(courses) {
    const section = document.getElementById('eligibleCoursesSection');
    const countEl = document.getElementById('eligibleCoursesCount');
    const tbody = document.getElementById('eligibleCoursesList');
    const empty = document.getElementById('eligibleEmptyState');

    // Không phải trang students hoặc chưa có UI này
    if (!section || !countEl || !tbody || !empty) {
        return;
    }

    const list = Array.isArray(courses) ? courses : [];
    countEl.textContent = String(list.length);
    tbody.innerHTML = '';

    if (!list.length) {
        empty.style.display = 'block';
        section.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    list.forEach((course, index) => {
        const row = document.createElement('tr');
        const reasonsText = (course.reasons && Array.isArray(course.reasons))
            ? course.reasons.join(', ')
            : '-';

        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${course.code || '-'}</td>
            <td>${course.name || '-'}</td>
            <td>${course.credits ?? 0}</td>
            <td>${reasonsText}</td>
        `;
        tbody.appendChild(row);
    });

    section.style.display = 'block';
}

/**
 * Chuẩn hóa hiển thị mục tiêu học tập
 */
function translateStudyGoal(goal) {
    const translations = {
        'đúng hạn': 'Học đúng hạn',
        'học vượt': 'Học vượt',
        'giảm tải': 'Giảm tải'
    };
    return translations[goal?.toLowerCase()] || goal || '-';
}

/**
 * Hiện thông báo lỗi
 */
function showError(message, type = 'error') {
    showToast(message, type);
}

/**
 * Mã hóa ký tự HTML đặc biệt
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initFlashToasts() {
    document.querySelectorAll('.flash-message[data-message]').forEach(item => {
        const message = item.dataset.message;
        const type = item.dataset.type || 'info';
        if (message) {
            showToast(message, type);
        }
        item.remove();
    });
}

function showToast(message, type = 'info', duration = 1500) {
    const container = document.getElementById('toastContainer');
    if (!container || !message) {
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Đóng thông báo');
    closeBtn.innerHTML = '&times;';

    const content = document.createElement('div');
    content.className = 'toast-message';
    content.textContent = message;

    const progress = document.createElement('div');
    progress.className = 'toast-progress';
    progress.style.animationDuration = `${duration}ms`;

    toast.appendChild(closeBtn);
    toast.appendChild(content);
    toast.appendChild(progress);
    container.appendChild(toast);

    const removeToast = () => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    };

    closeBtn.addEventListener('click', removeToast);
    window.setTimeout(removeToast, duration);
}
