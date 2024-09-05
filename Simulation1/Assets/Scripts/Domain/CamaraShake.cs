using UnityEngine;
using System.Collections;

public class CameraShake : MonoBehaviour
{
    [SerializeField] private float shakeAmount = 0.03f;
    [SerializeField] private float shakeDuration = 10f;
    private Vector3 initialPos;
    private float shakeTimer;
    public GameObject explote; // Prefab de la explosión
    public GameObject atomPrefab; // Prefab del átomo
    private GameObject atomInstance; // Instancia del átomo

    private Vector3 cameraNewPosition = new Vector3(18.08f, 33.46f, 15.81f); // Nueva posición de la cámara

    void Awake()
    {
        initialPos = transform.position;
    }

    void OnEnable()
    {
        shakeTimer = shakeDuration;
        InstantiateAtom();
    }

    void Update()
    {
        if (shakeTimer > 0)
        {
            transform.position = initialPos + Random.insideUnitSphere * shakeAmount;
            shakeTimer -= Time.deltaTime;
        }
        else
        {
            Destroy(atomInstance); // Destruye la instancia del átomo
            StartCoroutine(InstantiateExplosion()); // Instancia la explosión y maneja su destrucción
            transform.position = initialPos;
            this.enabled = false; // Desactiva el script después de completar el efecto
        }
    }

    // Método público para iniciar el efecto de shake desde otros scripts
    public void StartShake()
    {
        shakeTimer = shakeDuration;
        InstantiateAtom();
    }

    // Método para instanciar el átomo con ajuste en la posición
    private void InstantiateAtom()
    {
        if (atomInstance == null)
        {
            Vector3 atomPosition = initialPos;
            atomPosition.y -= 3; // Ajusta la posición en Y
            atomInstance = Instantiate(atomPrefab, atomPosition, Quaternion.identity);
        }
    }

    // Corutina para instanciar la explosión, destruirla después de un tiempo y mover la cámara
    private IEnumerator InstantiateExplosion()
    {
        Vector3 explosionPosition = initialPos;
        explosionPosition.y -= 3; // Ajusta la posición en Y
        GameObject explosionInstance = Instantiate(explote, explosionPosition, Quaternion.identity);
        yield return new WaitForSeconds(2f); // Espera el tiempo de animación de la explosión (ajusta según sea necesario)
        Destroy(explosionInstance); // Destruye la explosión después de la animación

        // Mueve la cámara a la nueva posición
        transform.position = cameraNewPosition;
    }
}
