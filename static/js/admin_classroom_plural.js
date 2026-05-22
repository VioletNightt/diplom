(function () {
    function classroomWord(count) {
        var lastTwo = count % 100;
        var last = count % 10;
        if (lastTwo >= 11 && lastTwo <= 14) {
            return 'кабинетов';
        }
        if (last === 1) {
            return 'кабинет';
        }
        if (last >= 2 && last <= 4) {
            return 'кабинета';
        }
        return 'кабинетов';
    }

    function updatePaginatorText() {
        if (!document.body.classList.contains('model-classroom')) {
            return;
        }
        document.querySelectorAll('nav.paginator').forEach(function (paginator) {
            paginator.childNodes.forEach(function (node) {
                if (node.nodeType !== Node.TEXT_NODE) {
                    return;
                }
                var match = node.textContent.match(/(\d+)\s+Кабинеты/);
                if (!match) {
                    return;
                }
                var count = Number(match[1]);
                node.textContent = node.textContent.replace(
                    match[0],
                    count + ' ' + classroomWord(count)
                );
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updatePaginatorText);
    } else {
        updatePaginatorText();
    }
})();
