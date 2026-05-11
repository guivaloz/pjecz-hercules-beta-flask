//
// DataTables - Delete or Recover
//
function deleteRecover(id, url, row, myInit) {
  $(id).prop("disabled", true); // Deshabilitar boton para evitar multiples clicks
  fetch(url, myInit)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        if (data.estatus == "A") {
          $(id).removeClass("btn-light");
          $(id).addClass("btn-outline-primary");
          $(id).html('<span class="mdi mdi-delete"></span>');
          $(row).removeClass("table-dark");
        } else {
          $(id).removeClass("btn-outline-primary");
          $(id).addClass("btn-light");
          $(id).html('<span class="mdi mdi-delete-restore"></span>');
          $(row).addClass("table-dark");
        }
        console.log(data.message);
      } else {
        console.log(data.message);
      }
      $(id).prop("disabled", false); // Habilitar boton
    })
    .catch((error) => {
      console.log(error);
    });
}
