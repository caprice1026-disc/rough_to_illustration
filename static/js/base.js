const autoDismiss = () => {
  document.querySelectorAll('.alert.flash-card').forEach((alertEl) => {
    setTimeout(() => {
      const alertInstance = bootstrap.Alert.getOrCreateInstance(alertEl);
      alertInstance.close();
    }, 5200);
  });
};

document.addEventListener('DOMContentLoaded', autoDismiss);
