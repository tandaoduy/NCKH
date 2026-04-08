/**
 * Main JavaScript for Course Recommendation System
 * Hệ Thống Gợi Ý Kế Hoạch Học Tập - Frontend Logic
 */

// ========== GLOBAL VARIABLES ==========
let allStudents = [];
let selectedStudent = null;

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', function () {
    console.log('Initializing students page...');
    if (document.getElementById('studentSelect')) {
        loadAllStudents();
    }
    initNavbarScroll();
    initFlashToasts();
});

// ========== NAVBAR SCROLL ANIMATION ==========
function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            // Add 'scrolled' class when page is scrolled down
            if (window.scrollY > 20) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }
}

// ========== STEP 1: LOAD STUDENTS ==========
async function loadAllStudents() {
    try {
        const response = await fetch('/api/students');
        const data = await response.json();

        if (data.success) {
            allStudents = data.data;
            console.log(`Loaded ${allStudents.length} students`);

            // Populate dropdown
            populateStudentSelect();
        } else {
            console.error('Error loading students:', data.error);
            showError('Không thể tải danh sách sinh viên');
        }
    } catch (error) {
        console.error('Fetch error:', error);
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

// ========== STEP 1: SEARCH STUDENT ==========
function searchStudent() {
    const searchInput = document.getElementById('studentSearch');
    const searchTerm = searchInput.value.trim().toUpperCase();

    if (!searchTerm) {
        showError('Vui lòng nhập mã sinh viên', 'warning');
        return;
    }

    // Find student
    const student = allStudents.find(s => s.student_id.toUpperCase() === searchTerm);
    if (student) {
        document.getElementById('studentSelect').value = student.student_id;
        onStudentSelected();
    } else {
        showError(`Không tìm thấy sinh viên: ${searchTerm}`);
    }
}

// ========== STEP 2: STUDENT SELECTED ==========
async function onStudentSelected() {
    const select = document.getElementById('studentSelect');
    const studentId = select.value;

    if (!studentId) {
        // Hide profile section if no student selected
        document.getElementById('studentProfileSection').style.display = 'none';
        document.getElementById('recommendationActionSection').style.display = 'none';
        return;
    }

    try {
        // Fetch full student profile
        const response = await fetch(`/api/students/${studentId}`);
        const data = await response.json();

        if (data.success) {
            selectedStudent = data.data;
            displayStudentProfile(selectedStudent);

            // Show profile and action sections
            document.getElementById('studentProfileSection').style.display = 'block';
            document.getElementById('recommendationActionSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
        } else {
            showError('Không thể tải thông tin sinh viên');
        }
    } catch (error) {
        console.error('Fetch error:', error);
        showError('Lỗi tải thông tin sinh viên');
    }
}

// ========== STEP 2: DISPLAY STUDENT PROFILE ==========
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

    // Display passed courses
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

    // Display failed courses
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

// ========== STEP 3: GENERATE RECOMMENDATION ==========
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
        console.error('Error:', error);
        showError(`Lỗi kế nối: ${error.message}`);
    } finally {
        generateBtn.disabled = false;
        spinnerDiv.style.display = 'none';
    }
}

// ========== STEP 4: DISPLAY RESULTS ==========
function displayRecommendationResults(data) {
    // Update summary stats
    const courses = data.recommended_courses || [];
    document.getElementById('resultTotalCourses').textContent = courses.length;
    document.getElementById('resultTotalCredits').textContent = data.total_recommended_credits || 0;
    
    // Calculate next semester from current student data
    if (selectedStudent && selectedStudent.current_semester) {
        const nextSemester = selectedStudent.current_semester + 1;
        document.getElementById('resultNextSemester').textContent = nextSemester;
    }

    // Display courses table - use the correct tbody ID
    const tableBody = document.getElementById('recommendedCoursesList');
    if (tableBody) {
        tableBody.innerHTML = '';

        courses.forEach((course, index) => {
            const row = document.createElement('tr');
            // Model uses: code, name, credits, heuristic_score, reasons (array)
            const reasonsText = (course.reasons && Array.isArray(course.reasons))
                ? course.reasons.join(', ')
                : '-';

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${course.code || '-'}</td>
                <td>${course.name || '-'}</td>
                <td>${course.credits || 0}</td>
                <td>${reasonsText}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    // Display algorithm details
    const detailsDiv = document.querySelector('.details-box');
    if (detailsDiv && data.explanation) {
        detailsDiv.innerHTML = `<pre>${escapeHtml(data.explanation)}</pre>`;
    }
}

// ========== HELPER FUNCTIONS ==========

/**
 * Translate study goal from Vietnamese
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
 * Show error message
 */
function showError(message, type = 'error') {
    showToast(message, type);
}

/**
 * Escape HTML special characters
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

function showToast(message, type = 'info', duration = 5000) {
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
