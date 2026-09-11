let qrScanner = null;

function startQRScanner() {
    const scannerBox = document.getElementById("qr-scanner-box");

    if (!scannerBox) {
        alert("Scanner box not found.");
        return;
    }

    scannerBox.style.display = "block";

    if (qrScanner) {
        qrScanner.clear();
    }

    qrScanner = new Html5Qrcode("qr-reader");

    qrScanner.start(
        { facingMode: "environment" },
        {
            fps: 10,
            qrbox: {
                width: 250,
                height: 250
            }
        },
        function(decodedText) {

            console.log("QR Code:", decodedText);

            document.getElementById("scanned-upi").value = decodedText;

            stopQRScanner();

            alert("QR Code scanned successfully!");
        },
        function(errorMessage) {
            // QR not detected yet
        }
    ).catch(function(error) {

        console.error("Camera error:", error);

        alert(
            "Camera could not be started. Please allow camera permission."
        );
    });
}


function stopQRScanner() {

    if (qrScanner) {

        qrScanner.stop()
            .then(function() {

                qrScanner.clear();

                const scannerBox =
                    document.getElementById("qr-scanner-box");

                if (scannerBox) {
                    scannerBox.style.display = "none";
                }

            })
            .catch(function(error) {

                console.error(
                    "Scanner stop error:",
                    error
                );

            });
    }
}
