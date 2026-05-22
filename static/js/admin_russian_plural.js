(function () {
    var dictionary = {
        classroom: {
            source: 'Кабинеты',
            forms: ['кабинет', 'кабинета', 'кабинетов'],
        },
        teacherprofile: {
            source: 'Профиль учителя',
            forms: ['профиль учителя', 'профиля учителей', 'профилей учителей'],
        },
        slot: {
            source: 'Слоты',
            forms: ['слот', 'слота', 'слотов'],
        },
    };

    function currentModel() {
        var classes = Array.prototype.slice.call(document.body.classList);
        var modelClass = classes.find(function (item) {
            return item.indexOf('model-') === 0;
        });
        return modelClass ? modelClass.replace('model-', '') : '';
    }

    function chooseForm(count, forms) {
        var lastTwo = count % 100;
        var last = count % 10;
        if (lastTwo >= 11 && lastTwo <= 14) {
            return forms[2];
        }
        if (last === 1) {
            return forms[0];
        }
        if (last >= 2 && last <= 4) {
            return forms[1];
        }
        return forms[2];
    }

    function updatePaginatorText() {
        var config = dictionary[currentModel()];
        if (!config) {
            return;
        }

        document.querySelectorAll('nav.paginator').forEach(function (paginator) {
            paginator.childNodes.forEach(function (node) {
                if (node.nodeType !== Node.TEXT_NODE) {
                    return;
                }
                var pattern = new RegExp('(\\d+)\\s+' + config.source);
                var match = node.textContent.match(pattern);
                if (!match) {
                    return;
                }
                var count = Number(match[1]);
                node.textContent = node.textContent.replace(
                    match[0],
                    count + ' ' + chooseForm(count, config.forms)
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
