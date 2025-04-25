document.getElementById('upForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    const formData = new FormData(this); // Create a FormData object from the form
    /* Upload file */
    fetch('/lab/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(data => {
        const msg = document.createElement('p');
        resp = JSON.parse(data)
        msg.innerText = resp['msg']
        document.getElementById('fList').prepend(msg); // Display the response from the server
    })
    .catch(error => {
        console.error('Error:', error);
    });
});


/* Get updated Filelist */
(function () {
    x = setInterval(function () {
        fetch('/lab/filelist', {
            method: 'GET'
        })
        .then(response => response.text())
        .then(data => {
            res = JSON.parse(data);

            /* Update dropdown options */
            var fl = document.getElementById('files');
            /*fl.innerHTML = '<option value="none" selected disabled>N/A</option>';*/
            for (let key in res) {
                if (res.hasOwnProperty(key)) {
                    child_check = document.getElementById(res[key]);
                    if (!fl.contains(child_check)) {
                        let option = document.createElement('option');
                        option.id = res[key];
                        option.value = res[key];
                        option.textContent = res[key];
                        fl.appendChild(option);
                    }
                }
            }

            /* update file list in side nav bar */
            var sn = document.getElementById('sub-flist');
            sn.innerHTML = '';
            for (let key in res) {
                if (res.hasOwnProperty(key)) {
                    let li = document.createElement('li');
                    li.style = "pointer-events:none;";
                    li.textContent = res[key];
                    sn.appendChild(li);
                }
            }
                
        })
        .catch(error => {
            console.error('Error:', error);
        });
    },500);
})();