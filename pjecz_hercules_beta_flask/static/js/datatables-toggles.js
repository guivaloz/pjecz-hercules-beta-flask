//
// DataTables Toggles
//
// Debe preparar headers para POST
//
//     // Preparar headers para toggleEsActivo
//     const myHeaders = new Headers();
//     myHeaders.append("X-CSRF-TOKEN", "{{ csrf_token() }}");
//     const myInit = {
//       method: "POST",
//       headers: myHeaders,
//       mode: "cors",
//       cache: "default",
//     };
//
function toggleEsActivo(id, url, row, myInit) {
  $(id).prop("disabled", true); // Deshabilitar boton para evitar multiples clicks
  fetch(url, myInit)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        if (data.es_activo) {
          $(id).removeClass("btn-light");
          $(id).removeClass("btn-outline-dark");
          $(id).addClass("btn-primary");
          $(id).addClass("btn-outline-primary");
          $(id).html('<span class="mdi mdi-toggle-switch"></span>');
        } else {
          $(id).removeClass("btn-primary");
          $(id).removeClass("btn-outline-primary");
          $(id).addClass("btn-light");
          $(id).addClass("btn-outline-dark");
          $(id).html('<span class="mdi-toggle-switch-off"></span>');
        }
        // console.log(data.message);
        console.log(row);
      } else {
        console.log(data.message);
      }
      $(id).prop("disabled", false); // Habilitar boton
    })
    .catch((error) => {
      console.log(error);
    });
}
