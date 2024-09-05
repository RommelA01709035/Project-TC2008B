using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Networking;

[System.Serializable]
public class Cell
{
    public int alert;
    public string door;
    public bool down;
    public bool entrance;
    public int fire;
    public int is_agent;
    public bool left;
    public string pos;
    public bool right;
    public bool up;

    public bool entrada;
    public int entryPoints;
    public List<List<int>> coordenadas_victimas;
    public List<List<int>> coordenadas_fuego;
    public List<List<int>> coordenadas_doors;
    public List<List<int>> coordenadas_entradas;
    public List<List<int>> coordenadas_poi;
    public int step;
}

public class WebClient : MonoBehaviour
{
    public GameObject cellPrefab;
    public GameObject wallPrefab;
    public GameObject explotionrefab;

    public GameObject firePrefab;
    public GameObject smokePrefab;
    public GameObject agentPrefab;
    public GameObject victimPrefab;
    public GameObject doorPrefab;
    public GameObject poiPrefab;
    public GameObject entryPointPrefab;
    public GameObject floor;
    public int maxDocuments = 80; // Número máximo de documentos a procesar
    public float delay = 1.0f;
    private string previousJson = "";
    private Dictionary<string, Cell> currentCellDictionary;

    IEnumerator SendData()
{
    string url = "http://127.0.0.1:5000";
    int stepCounter = 0;  // Inicializar el contador de pasos
    while (true)
    {
        using (UnityWebRequest www = UnityWebRequest.Get(url))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.ConnectionError || www.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"Error: {www.error}, Status Code: {www.responseCode}");
            }
            else
            {
                string newJson = www.downloadHandler.text;
                if (!newJson.Equals(previousJson))
                {
                    currentCellDictionary = JsonConvert.DeserializeObject<Dictionary<string, Cell>>(newJson);

                    // Actualizar el valor de step en cada celda antes de procesar
                    foreach (var cell in currentCellDictionary.Values)
                    {
                        cell.step = stepCounter;  // Actualizar con el nuevo valor de step
                    }

                    // Procesar solo los primeros 'maxDocuments' documentos
                    CrearEscenario(currentCellDictionary, maxDocuments);
                    Debug.Log(newJson);
                    previousJson = newJson;
                    Debug.Log($"Data processed at step {stepCounter}.");
                    
                    stepCounter++;  // Incrementar el contador de pasos
                    yield return new WaitForSeconds(delay);
                }
                else
                {
                    Debug.Log("No changes detected in the JSON.");
                }
            }
        }
    }
}


    void LoadResourcesForCell(Cell cell, Vector3 cellPosition)
    {
        CreateAgentPrefab(cellPosition, cell);
        CreateDoorPrefabs(cellPosition, cell);
        CreateWallPrefabs(cellPosition, cell, GetPrefabSize(cellPrefab));
        if (cell.is_agent >= 1)
        {
            CreateAgentPrefab(cellPosition, cell);
        }
        if (cell.fire == 2)
        {
            CreateFirePrefab(cellPosition, cell);
        }
        else if (cell.fire == 1)
        {
            CreateSmokePrefab(cellPosition, cell);
        }
        if (cell.alert > 0)
        {
            CreatePOIPrefab(cellPosition, cell);
        }
        Debug.Log($"Loaded resources for step {cell.step} at position {cellPosition}");
    }

    void CrearEscenario(Dictionary<string, Cell> cellDictionary, int maxCount)
    {
        int currentRow = 0;
        int currentColumn = 0;

        Vector3 cellSize = GetPrefabSize(cellPrefab);
        int count = 0;

        foreach (var entry in cellDictionary)
        {
            if (count >= maxCount)
            {
                Debug.Log("Max count reached.");
                break;
            }

            string cellId = entry.Key;
            Cell cell = entry.Value;

            Vector3 cellPosition = new Vector3(currentColumn * cellSize.x, 0.25f, currentRow * cellSize.z);

            CreateDoorPrefabs(cellPosition, cell);
            InstanciarCelda(cellPosition);
            CreateWallPrefabs(cellPosition, cell, cellSize);
            CreateAgentPrefab(cellPosition, cell);

            if (cell.fire == 2)
            {
                CreateFirePrefab(cellPosition, cell);
            }
            if (cell.fire == 1)
            {
                CreateSmokePrefab(cellPosition, cell);
            }
            if (cell.entrance)
            {
                //CreateEntryPointPrefab(cellPosition, cell);
            }
            if (cell.alert == 1 || cell.alert == 2)
            {
                CreatePOIPrefab(cellPosition, cell);
            }

            currentColumn++;
            if (currentColumn >= 10)
            {
                currentColumn = 0;
                currentRow++;
            }

            count++;
        }
    }

    void CreateAgentPrefab(Vector3 basePosition, Cell cell)
    {
        if (cell.is_agent >= 1)
        {
            GameObject agentObject = Instantiate(agentPrefab, basePosition, Quaternion.identity);
            agentObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated agent at position {basePosition}");
        }
    }

    void InstanciarCelda(Vector3 position)
    {
        GameObject nuevaCeldaGO = Instantiate(cellPrefab, position, Quaternion.identity);
        nuevaCeldaGO.transform.SetParent(floor.transform);
    }

    void CreateDoorPrefabs(Vector3 basePosition, Cell cell)
    {
        string[] doors = cell.door.Trim(new char[] { '[', ']', ' ' }).Split(',');

        foreach (string doorString in doors)
        {
            string door = doorString.Trim();

            if (door.StartsWith("(") && door.EndsWith(")"))
            {
                string[] coords = door.Substring(1, door.Length - 2).Split(',');

                if (coords.Length == 2 &&
                    int.TryParse(coords[0], out int doorRow) &&
                    int.TryParse(coords[1], out int doorCol))
                {
                    Vector3 doorPosition = basePosition + new Vector3(doorCol * 1.5f, 1, doorRow * 1.5f);
                    GameObject doorObject = Instantiate(doorPrefab, doorPosition, Quaternion.identity);
                    doorObject.transform.SetParent(floor.transform);
                    Debug.Log($"Instantiated door at position {doorPosition}");
                }
                else
                {
                    Debug.LogWarning($"Invalid door coordinates: {door}");
                }
            }
        }
    }

    void CreateWallPrefabs(Vector3 basePosition, Cell cell, Vector3 cellSize)
    {
        float wallOffset = cellSize.x / 2.0f - 0.1f;

        if (cell.left)
        {
            Vector3 wallPosition = basePosition + new Vector3(-wallOffset - 1, 4, -3);
            GameObject wallObject = Instantiate(wallPrefab, wallPosition, Quaternion.Euler(0, 90, 0));
            wallObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated wall on the left at position {wallPosition}");
        }
        if (cell.right)
        {
            Vector3 wallPosition = basePosition + new Vector3(wallOffset - 1, 4, -3);
            GameObject wallObject = Instantiate(wallPrefab, wallPosition, Quaternion.Euler(0, 90, 0));
            wallObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated wall on the right at position {wallPosition}");
        }
        if (cell.up)
        {
            Vector3 wallPosition = basePosition + new Vector3(0, 4, wallOffset - 4.1f);
            GameObject wallObject = Instantiate(wallPrefab, wallPosition, Quaternion.Euler(0, 0, 0));
            wallObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated wall up at position {wallPosition}");
        }
        if (cell.down)
        {
            Vector3 wallPosition = basePosition + new Vector3(0, 4, -wallOffset + 4.1f);
            GameObject wallObject = Instantiate(wallPrefab, wallPosition, Quaternion.Euler(0, 0, 0));
            wallObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated wall down at position {wallPosition}");
        }
    }

    void CreateFirePrefab(Vector3 basePosition, Cell cell)
    {
        if (cell.fire == 2)
        {
            Vector3 firePosition = basePosition + new Vector3(0, 0, 0);
            GameObject fireObject = Instantiate(firePrefab, firePosition, Quaternion.identity);
            fireObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated fire at position {firePosition}");
        }
    }

    void CreateSmokePrefab(Vector3 basePosition, Cell cell)
    {
        if (cell.fire == 1)
        {
            Vector3 smokePosition = basePosition + new Vector3(0, 0, 0);
            GameObject smokeObject = Instantiate(smokePrefab, smokePosition, Quaternion.identity);
            smokeObject.transform.SetParent(floor.transform);
            Debug.Log($"Instantiated smoke at position {smokePosition}");
        }
    }

    void CreatePOIPrefab(Vector3 basePosition, Cell cell)
    {
        Vector3 poiPosition = basePosition + new Vector3(0, 0, 0);
        GameObject poiObject = Instantiate(poiPrefab, poiPosition, Quaternion.identity);
        poiObject.transform.SetParent(floor.transform);
        Debug.Log($"Instantiated POI at position {poiPosition}");
    }

    void CreateEntryPointPrefab(Vector3 basePosition, Cell cell)
    {
        Vector3 entryPointPosition = basePosition + new Vector3(0, 0, 0);
        GameObject entryPointObject = Instantiate(entryPointPrefab, entryPointPosition, Quaternion.identity);
        entryPointObject.transform.SetParent(floor.transform);
        Debug.Log($"Instantiated entry point at position {entryPointPosition}");
    }

    Vector3 GetPrefabSize(GameObject prefab)
    {
        Renderer renderer = prefab.GetComponent<Renderer>();
        if (renderer != null)
        {
            return renderer.bounds.size;
        }
        else
        {
            Debug.LogWarning("Prefab does not have a Renderer component. Returning Vector3.one as size.");
            return Vector3.one;
        }
    }

    void Start()
    {
        StartCoroutine(SendData());
    }
}
